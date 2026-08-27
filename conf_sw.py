#!/usr/bin/env python3
"""
------------------------------------------------------------
Aplicação GUI para configuração de switches Cisco
com Tkinter - baseada no script original
com suporte a backup via TFTP e GitHub
------------------------------------------------------------
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import threading
import logging
import time
from datetime import datetime
from netmiko import ConnectHandler
from netmiko.exceptions import NetmikoTimeoutException, NetmikoAuthenticationException
import requests
import base64
import os

# Importa os templates do arquivo externo
try:
    from template import CONFIG_COMMANDS, VLAN_COMMANDS
except ImportError:
    CONFIG_COMMANDS = ["hostname Switch"]
    VLAN_COMMANDS = ["vlan 10", "name VLAN_DADOS", "vlan 20", "name VLAN_VOZ", "vlan 50", "name VLAN_SEGURANCA"]
    print("[!] template.py não encontrado. Usando comandos padrão.")

logging.basicConfig(
    filename="netmiko_session.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("netmiko")

# =============================================================================
# FUNÇÕES DE CONFIGURAÇÃO (adaptadas para aceitar um callback de saída)
# =============================================================================

def conectar_switch(device, output_callback):
    try:
        output_callback(f"[+] Conectando ao switch {device['ip']} via {device['device_type']} (telnet)...\n")
        conn = ConnectHandler(**device)
        output_callback("[+] Conexão estabelecida com sucesso.\n")
        return conn
    except NetmikoAuthenticationException:
        output_callback("[!] Falha de autenticação.\n")
        raise
    except NetmikoTimeoutException:
        output_callback("[!] Timeout ao conectar.\n")
        raise

def entrar_modo_enable(conn, output_callback):
    if not conn.check_enable_mode():
        output_callback("[+] Elevando para modo privilegiado (enable)...\n")
        try:
            conn.enable()
        except Exception as e:
            output_callback(f"[!] Não foi possível usar 'enable': {e}\n")
    else:
        output_callback("[+] Já está em modo privilegiado.\n")

def ajustar_horario_switch(conn, output_callback):
    agora = datetime.now()
    comando = agora.strftime("clock set %H:%M:%S %d %B %Y")
    output_callback(f"[+] Ajustando relógio do switch: {comando}\n")
    try:
        output = conn.send_command(comando, expect_string=r"#")
        output_callback(output + "\n")
        return output
    except Exception as e:
        output_callback(f"[!] Erro ao ajustar horário: {e}\n")
        return ""

def aplicar_vlans_database(conn, vlan_commands, output_callback):
    if not vlan_commands:
        return ""
    output_callback("[+] Configurando VLANs via 'vlan database'...\n")
    try:
        output = conn.send_command_timing("vlan database")
        for cmd in vlan_commands:
            output += conn.send_command_timing(cmd)
        output += conn.send_command_timing("apply")
        output += conn.send_command_timing("exit")
        output_callback(output + "\n")
        time.sleep(1)
        conn.clear_buffer()
        try:
            conn.find_prompt()
        except Exception:
            pass
        return output
    except Exception as e:
        output_callback(f"[!] Erro ao configurar VLANs: {e}\n")
        return ""

def aplicar_configuracao(conn, comandos, output_callback):
    output_callback("[+] Aplicando template de configuração...\n")
    try:
        output = conn.send_config_set(comandos)
        output_callback(output + "\n")
        return output
    except Exception as e:
        output_callback(f"[!] send_config_set falhou ({e}). Tentando modo manual...\n")
        output = conn.send_command_timing("configure terminal")
        for cmd in comandos:
            output += conn.send_command_timing(cmd)
        output += conn.send_command_timing("end")
        output_callback(output + "\n")
        return output

def salvar_configuracao(conn, output_callback):
    output_callback("[+] Salvando configuração (write memory)...\n")
    try:
        output = conn.send_command("write memory", expect_string=r"#")
        output_callback(output + "\n")
        return output
    except Exception as e:
        output_callback(f"[!] Erro ao salvar: {e}\n")
        return ""

def backup_configuracao(conn, arquivo="backup_running_config.txt", output_callback=None):
    output_callback("[+] Fazendo backup da running-config...\n")
    try:
        output = conn.send_command("show running-config")
        with open(arquivo, "w") as f:
            f.write(output)
        output_callback(f"[+] Backup salvo em: {arquivo}\n")
        return output
    except Exception as e:
        output_callback(f"[!] Erro no backup: {e}\n")
        return ""

# =============================================================================
# FUNÇÕES ESPECÍFICAS PARA VALIDAÇÃO E BACKUP TFTP (CORRIGIDAS)
# =============================================================================

def validar_configuracao(device, output_callback):
    """
    Valida:
      - Hostname (comparando com o template)
      - VLANs existentes (usando show vlan-switch brief)
    """
    conn = None
    try:
        conn = conectar_switch(device, output_callback)
        entrar_modo_enable(conn, output_callback)
        
        # Obtém hostname esperado
        hostname_esperado = None
        for cmd in CONFIG_COMMANDS:
            if cmd.strip().startswith("hostname"):
                hostname_esperado = cmd.strip().split()[1]
                break
        
        # 1) Verifica hostname (usando show running-config | include hostname)
        if hostname_esperado:
            output = conn.send_command("show running-config | include hostname")
            linhas = output.splitlines()
            if linhas:
                hostname_atual = linhas[0].strip().split()[1]
                if hostname_atual == hostname_esperado:
                    output_callback(f"[OK] Hostname correto: {hostname_atual}\n")
                else:
                    output_callback(f"[FALHA] Hostname esperado: {hostname_esperado}, atual: {hostname_atual}\n")
            else:
                output_callback("[FALHA] Não foi possível encontrar hostname na configuração.\n")
        else:
            output_callback("[AVISO] Nenhum comando 'hostname' encontrado no template para validação.\n")
        
        # 2) Verifica VLANs usando show vlan-switch brief (ou show vlan brief)
        vlan_esperadas = []
        for cmd in VLAN_COMMANDS:
            if cmd.strip().startswith("vlan"):
                partes = cmd.strip().split()
                if len(partes) > 1 and partes[1].isdigit():
                    vlan_esperadas.append(partes[1])
        if vlan_esperadas:
            try:
                output = conn.send_command("show vlan-switch brief")
            except:
                output = conn.send_command("show vlan brief")
            vlans_existentes = []
            for linha in output.splitlines():
                if linha.strip() and linha[0].isdigit():
                    vlan_id = linha.strip().split()[0]
                    if vlan_id.isdigit():
                        vlans_existentes.append(vlan_id)
            for v in vlan_esperadas:
                if v in vlans_existentes:
                    output_callback(f"[OK] VLAN {v} criada.\n")
                else:
                    output_callback(f"[FALHA] VLAN {v} não encontrada.\n")
        else:
            output_callback("[AVISO] Nenhuma VLAN definida no template para validação.\n")
        
    except Exception as e:
        output_callback(f"[!] Erro durante validação: {e}\n")
    finally:
        if conn:
            conn.disconnect()
            output_callback("[+] Conexão encerrada.\n")

def backup_tftp(device, tftp_server, output_callback):
    """
    Envia a running-config para um servidor TFTP usando send_command com expect_string.
    """
    conn = None
    try:
        conn = conectar_switch(device, output_callback)
        entrar_modo_enable(conn, output_callback)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        hostname = conn.send_command("show running-config | include hostname").strip().split()[-1]
        filename = f"{hostname}_{timestamp}.cfg"
        
        output_callback(f"[+] Enviando configuração para TFTP servidor {tftp_server}, arquivo {filename}...\n")
        
        output = conn.send_command(
            "copy running-config tftp:",
            expect_string=r"Address or name of remote host",
            strip_prompt=False,
            strip_command=False
        )
        output_callback(output)
        
        output = conn.send_command(
            tftp_server,
            expect_string=r"Destination filename",
            strip_prompt=False,
            strip_command=False
        )
        output_callback(output)
        
        output = conn.send_command(
            filename,
            expect_string=r"#",
            strip_prompt=False,
            strip_command=False
        )
        output_callback(output + "\n")
        
        output_callback("[+] Backup TFTP concluído.\n")
        
    except Exception as e:
        output_callback(f"[!] Erro no backup TFTP: {e}\n")
    finally:
        if conn:
            conn.disconnect()
            output_callback("[+] Conexão encerrada.\n")

# =============================================================================
# FUNÇÃO PARA BACKUP NO GITHUB
# =============================================================================

def backup_github(device, github_token, github_repo, output_callback):
    """
    Faz backup da running-config e envia para o GitHub via API.
    """
    conn = None
    try:
        conn = conectar_switch(device, output_callback)
        entrar_modo_enable(conn, output_callback)
        
        # Obtém a running-config
        output_callback("[+] Obtendo running-config...\n")
        running_config = conn.send_command("show running-config")
        
        # Nome do arquivo com timestamp e hostname
        hostname = "switch"  # fallback
        for line in running_config.splitlines():
            if line.strip().startswith("hostname"):
                hostname = line.strip().split()[1]
                break
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{hostname}_{timestamp}.cfg"
        
        output_callback(f"[+] Enviando arquivo {filename} para o repositório {github_repo}...\n")
        
        # Prepara a requisição para a API do GitHub
        url = f"https://api.github.com/repos/{github_repo}/contents/{filename}"
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json"
        }
        # Conteúdo codificado em base64
        content_b64 = base64.b64encode(running_config.encode()).decode()
        data = {
            "message": f"Backup automático do switch {hostname} em {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "content": content_b64,
            "branch": "main"  # ou "master" - ajuste conforme necessário
        }
        
        response = requests.put(url, headers=headers, json=data)
        if response.status_code == 201:
            output_callback(f"[+] Backup enviado com sucesso! Arquivo: {filename}\n")
            output_callback(f"    URL: {response.json()['content']['html_url']}\n")
        elif response.status_code == 422:
            output_callback("[!] Arquivo já existe? Tentando atualizar...\n")
            # Se o arquivo já existe, precisamos obter o SHA e fazer PUT com o SHA
            # Primeiro, obtém informações do arquivo existente
            get_response = requests.get(url, headers=headers)
            if get_response.status_code == 200:
                sha = get_response.json()['sha']
                data['sha'] = sha
                update_response = requests.put(url, headers=headers, json=data)
                if update_response.status_code == 200:
                    output_callback(f"[+] Backup atualizado com sucesso! Arquivo: {filename}\n")
                    output_callback(f"    URL: {update_response.json()['content']['html_url']}\n")
                else:
                    output_callback(f"[!] Falha ao atualizar: {update_response.status_code} - {update_response.text}\n")
            else:
                output_callback(f"[!] Não foi possível obter informações do arquivo: {get_response.status_code}\n")
        else:
            output_callback(f"[!] Falha ao enviar para GitHub: {response.status_code} - {response.text}\n")
        
    except Exception as e:
        output_callback(f"[!] Erro no backup GitHub: {e}\n")
    finally:
        if conn:
            conn.disconnect()
            output_callback("[+] Conexão encerrada.\n")

# =============================================================================
# CLASSE DA INTERFACE GRÁFICA
# =============================================================================

class App:
    def __init__(self, root):
        self.root = root
        root.title("Configurador de Switches Cisco")
        root.geometry("800x700")  # Aumentei um pouco para mais campos
        root.grid_rowconfigure(2, weight=1)
        root.grid_columnconfigure(0, weight=1)
        
        frame_config = ttk.LabelFrame(root, text="Parâmetros de Conexão", padding=10)
        frame_config.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        frame_config.grid_columnconfigure(1, weight=1)
        
        # Linha 0
        ttk.Label(frame_config, text="IP:").grid(row=0, column=0, sticky="w", padx=5)
        self.ip_entry = ttk.Entry(frame_config, width=20)
        self.ip_entry.grid(row=0, column=1, sticky="w", padx=5)
        self.ip_entry.insert(0, "172.26.102.129")
        
        ttk.Label(frame_config, text="Usuário:").grid(row=0, column=2, sticky="w", padx=5)
        self.user_entry = ttk.Entry(frame_config, width=15)
        self.user_entry.grid(row=0, column=3, sticky="w", padx=5)
        self.user_entry.insert(0, "admin")
        
        # Linha 1
        ttk.Label(frame_config, text="Senha:").grid(row=1, column=0, sticky="w", padx=5)
        self.pass_entry = ttk.Entry(frame_config, width=20, show="*")
        self.pass_entry.grid(row=1, column=1, sticky="w", padx=5)
        self.pass_entry.insert(0, "12345678")
        
        ttk.Label(frame_config, text="Porta Telnet:").grid(row=1, column=2, sticky="w", padx=5)
        self.port_entry = ttk.Entry(frame_config, width=10)
        self.port_entry.grid(row=1, column=3, sticky="w", padx=5)
        self.port_entry.insert(0, "5002")
        
        # Linha 2 - TFTP
        ttk.Label(frame_config, text="TFTP Server:").grid(row=2, column=0, sticky="w", padx=5)
        self.tftp_entry = ttk.Entry(frame_config, width=20)
        self.tftp_entry.grid(row=2, column=1, sticky="w", padx=5)
        self.tftp_entry.insert(0, " ")
        
        # Linha 3 - GitHub
        ttk.Label(frame_config, text="GitHub Token:").grid(row=3, column=0, sticky="w", padx=5)
        self.github_token_entry = ttk.Entry(frame_config, width=30, show="*")
        self.github_token_entry.grid(row=3, column=1, columnspan=3, sticky="w", padx=5)
        self.github_token_entry.insert(0, "INSER TOKEN")
        
        ttk.Label(frame_config, text="Repositório (user/repo):").grid(row=4, column=0, sticky="w", padx=5)
        self.github_repo_entry = ttk.Entry(frame_config, width=30)
        self.github_repo_entry.grid(row=4, column=1, columnspan=3, sticky="w", padx=5)
        self.github_repo_entry.insert(0, "gio128/autoconf")
        
        frame_botoes = ttk.Frame(root)
        frame_botoes.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        
        self.btn_start = ttk.Button(frame_botoes, text="Iniciar Configuração", command=self.iniciar_configuracao)
        self.btn_start.pack(side=tk.LEFT, padx=5)
        
        self.btn_validate = ttk.Button(frame_botoes, text="Validar Configuração", command=self.validar)
        self.btn_validate.pack(side=tk.LEFT, padx=5)
        
        self.btn_backup_tftp = ttk.Button(frame_botoes, text="Backup via TFTP", command=self.backup_tftp)
        self.btn_backup_tftp.pack(side=tk.LEFT, padx=5)
        
        self.btn_backup_github = ttk.Button(frame_botoes, text="Backup para GitHub", command=self.backup_github)
        self.btn_backup_github.pack(side=tk.LEFT, padx=5)
        
        self.btn_clear = ttk.Button(frame_botoes, text="Limpar Saída", command=self.limpar_saida)
        self.btn_clear.pack(side=tk.LEFT, padx=5)
        
        frame_output = ttk.LabelFrame(root, text="Saída", padding=5)
        frame_output.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        frame_output.grid_rowconfigure(0, weight=1)
        frame_output.grid_columnconfigure(0, weight=1)
        
        self.output_text = scrolledtext.ScrolledText(frame_output, wrap=tk.WORD, state='normal')
        self.output_text.grid(row=0, column=0, sticky="nsew")
        self.output_text.config(font=("Courier", 10))
        
        self.running = False
        
    def limpar_saida(self):
        self.output_text.delete(1.0, tk.END)
    
    def escrever_saida(self, texto):
        self.output_text.insert(tk.END, texto)
        self.output_text.see(tk.END)
        self.root.update_idletasks()
    
    def obter_device(self):
        return {
            "device_type": "cisco_ios_telnet",
            "ip": self.ip_entry.get().strip(),
            "username": self.user_entry.get().strip(),
            "password": self.pass_entry.get().strip(),
            "secret": "",
            "port": int(self.port_entry.get().strip()) if self.port_entry.get().strip().isdigit() else 5002,
            "timeout": 15,
        }
    
    def executar_em_thread(self, func, *args, **kwargs):
        if self.running:
            self.escrever_saida("[!] Uma operação já está em andamento. Aguarde.\n")
            return
        self.running = True
        for btn in [self.btn_start, self.btn_validate, self.btn_backup_tftp, self.btn_backup_github]:
            btn.config(state=tk.DISABLED)
        
        def wrapper():
            try:
                func(*args, **kwargs)
            except Exception as e:
                self.escrever_saida(f"[!] Erro inesperado: {e}\n")
            finally:
                self.running = False
                for btn in [self.btn_start, self.btn_validate, self.btn_backup_tftp, self.btn_backup_github]:
                    btn.config(state=tk.NORMAL)
        threading.Thread(target=wrapper, daemon=True).start()
    
    def iniciar_configuracao(self):
        self.escrever_saida("\n=== INICIANDO CONFIGURAÇÃO ===\n")
        self.executar_em_thread(self._thread_config)
    
    def _thread_config(self):
        device = self.obter_device()
        conn = None
        try:
            conn = conectar_switch(device, self.escrever_saida)
            entrar_modo_enable(conn, self.escrever_saida)
            ajustar_horario_switch(conn, self.escrever_saida)
            aplicar_vlans_database(conn, VLAN_COMMANDS, self.escrever_saida)
            aplicar_configuracao(conn, CONFIG_COMMANDS, self.escrever_saida)
            salvar_configuracao(conn, self.escrever_saida)
            self.escrever_saida("[+] Configuração finalizada com sucesso.\n")
        except Exception as e:
            self.escrever_saida(f"[!] Erro na configuração: {e}\n")
        finally:
            if conn:
                conn.disconnect()
                self.escrever_saida("[+] Conexão encerrada.\n")
    
    def validar(self):
        self.escrever_saida("\n=== VALIDANDO CONFIGURAÇÃO ===\n")
        self.executar_em_thread(self._thread_validar)
    
    def _thread_validar(self):
        device = self.obter_device()
        validar_configuracao(device, self.escrever_saida)
    
    def backup_tftp(self):
        tftp_ip = self.tftp_entry.get().strip()
        if not tftp_ip:
            self.escrever_saida("[!] Informe o IP do servidor TFTP.\n")
            return
        self.escrever_saida(f"\n=== ENVIANDO BACKUP TFTP para {tftp_ip} ===\n")
        self.executar_em_thread(self._thread_backup_tftp, tftp_ip)
    
    def _thread_backup_tftp(self, tftp_ip):
        device = self.obter_device()
        backup_tftp(device, tftp_ip, self.escrever_saida)
    
    def backup_github(self):
        token = self.github_token_entry.get().strip()
        repo = self.github_repo_entry.get().strip()
        if not token or not repo:
            self.escrever_saida("[!] Preencha o Token e o Repositório do GitHub.\n")
            return
        self.escrever_saida(f"\n=== ENVIANDO BACKUP PARA GITHUB ({repo}) ===\n")
        self.executar_em_thread(self._thread_backup_github, token, repo)
    
    def _thread_backup_github(self, token, repo):
        device = self.obter_device()
        backup_github(device, token, repo, self.escrever_saida)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()