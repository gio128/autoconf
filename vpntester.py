#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import threading
import datetime
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

try:
    from netmiko import (
        ConnectHandler,
        NetmikoTimeoutException,
        NetmikoAuthenticationException,
    )
except ImportError:
    raise SystemExit(
        "A biblioteca 'netmiko' não está instalada.\n"
        "Instale com: pip install netmiko"
    )


# --------------------------------------------------------------------------
# Mapeamento de device_type do Netmiko para cada fabricante
# --------------------------------------------------------------------------
DEVICE_TYPES = {
    "FortiGate": "fortinet",
    "Palo Alto": "paloalto_panos",
}

# --------------------------------------------------------------------------
# Conjuntos de comandos de diagnóstico de VPN para cada plataforma
# Comandos "fixos" (sempre executados) e "opcionais" (dependem de
# tunnel name / IP remoto informados pelo usuário)
# --------------------------------------------------------------------------
FORTIGATE_FIXED_CMDS = [
    "get vpn ipsec tunnel summary",
    "diagnose vpn ike gateway list",
    "diagnose vpn tunnel list",
    "get router info routing-table all",
]

FORTIGATE_TUNNEL_CMDS = [
    "diagnose vpn tunnel list name {tunnel}",
    "diagnose vpn ike gateway list name {tunnel}",
]

FORTIGATE_PING_CMD = "execute ping {ip}"

PALOALTO_FIXED_CMDS = [
    "show vpn ike-sa",
    "show vpn ipsec-sa",
    "show vpn flow",
    "show vpn tunnel",
    "show routing route",
]

PALOALTO_TUNNEL_CMDS = [
    "show vpn flow name {tunnel}",
    "test vpn ipsec-sa tunnel {tunnel}",
]

PALOALTO_PING_CMD = "ping count 4 host {ip}"


class VPNTesterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VPN Tester - FortiGate / Palo Alto")
        self.root.geometry("820x640")
        self.root.minsize(760, 560)

        self._build_form()
        self._build_output()

    # ------------------------------------------------------------------
    # Construção da interface
    # ------------------------------------------------------------------
    def _build_form(self):
        frame = ttk.LabelFrame(self.root, text="Dados de conexão")
        frame.pack(fill="x", padx=10, pady=10)

        # Fabricante
        ttk.Label(frame, text="Fabricante:").grid(row=0, column=0, sticky="w", padx=5, pady=5)
        self.vendor_var = tk.StringVar(value="FortiGate")
        vendor_combo = ttk.Combobox(
            frame, textvariable=self.vendor_var, values=list(DEVICE_TYPES.keys()),
            state="readonly", width=15
        )
        vendor_combo.grid(row=0, column=1, sticky="w", padx=5, pady=5)

        # IP
        ttk.Label(frame, text="IP do equipamento:").grid(row=0, column=2, sticky="w", padx=5, pady=5)
        self.ip_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.ip_var, width=20).grid(row=0, column=3, sticky="w", padx=5, pady=5)

        # Porta SSH
        ttk.Label(frame, text="Porta SSH:").grid(row=0, column=4, sticky="w", padx=5, pady=5)
        self.port_var = tk.StringVar(value="22")
        ttk.Entry(frame, textvariable=self.port_var, width=6).grid(row=0, column=5, sticky="w", padx=5, pady=5)

        # Usuário
        ttk.Label(frame, text="Usuário:").grid(row=1, column=0, sticky="w", padx=5, pady=5)
        self.user_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.user_var, width=20).grid(row=1, column=1, sticky="w", padx=5, pady=5)

        # Senha
        ttk.Label(frame, text="Senha:").grid(row=1, column=2, sticky="w", padx=5, pady=5)
        self.pass_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.pass_var, show="*", width=20).grid(row=1, column=3, sticky="w", padx=5, pady=5)

        # Nome do túnel (opcional)
        ttk.Label(frame, text="Nome do túnel (opcional):").grid(row=2, column=0, sticky="w", padx=5, pady=5)
        self.tunnel_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.tunnel_var, width=20).grid(row=2, column=1, sticky="w", padx=5, pady=5)

        # IP remoto para ping (opcional)
        ttk.Label(frame, text="IP remoto p/ ping (opcional):").grid(row=2, column=2, sticky="w", padx=5, pady=5)
        self.ping_ip_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.ping_ip_var, width=20).grid(row=2, column=3, sticky="w", padx=5, pady=5)

        # Botões
        btn_frame = ttk.Frame(self.root)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.run_btn = ttk.Button(btn_frame, text="Rodar testes de VPN", command=self.run_tests_thread)
        self.run_btn.pack(side="left", padx=5)

        ttk.Button(btn_frame, text="Limpar saída", command=self.clear_output).pack(side="left", padx=5)

        self.status_var = tk.StringVar(value="Pronto.")
        ttk.Label(btn_frame, textvariable=self.status_var, foreground="gray").pack(side="left", padx=15)

    def _build_output(self):
        out_frame = ttk.LabelFrame(self.root, text="Resultado dos testes")
        out_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.output_text = scrolledtext.ScrolledText(
            out_frame, wrap="word", font=("Consolas", 10), bg="#0d1117", fg="#c9d1d9"
        )
        self.output_text.pack(fill="both", expand=True, padx=5, pady=5)
        self.output_text.tag_config("header", foreground="#58a6ff")
        self.output_text.tag_config("cmd", foreground="#e3b341")
        self.output_text.tag_config("error", foreground="#f85149")
        self.output_text.tag_config("ok", foreground="#3fb950")

    # ------------------------------------------------------------------
    # Utilitários de escrita na área de saída (thread-safe via .after)
    # ------------------------------------------------------------------
    def log(self, msg, tag=None):
        def _write():
            self.output_text.insert("end", msg + "\n", tag)
            self.output_text.see("end")
        self.root.after(0, _write)

    def clear_output(self):
        self.output_text.delete("1.0", "end")

    def set_status(self, text):
        self.root.after(0, lambda: self.status_var.set(text))

    # ------------------------------------------------------------------
    # Validação e disparo em thread separada (não travar a GUI)
    # ------------------------------------------------------------------
    def run_tests_thread(self):
        ip = self.ip_var.get().strip()
        user = self.user_var.get().strip()
        password = self.pass_var.get()
        vendor = self.vendor_var.get()
        port = self.port_var.get().strip() or "22"

        if not ip or not user or not password:
            messagebox.showwarning("Preencha IP, usuário e senha.")
            return

        try:
            port = int(port)
        except ValueError:
            messagebox.showwarning("Porta inválida")
            return

        self.run_btn.config(state="disabled")
        self.set_status("Conectando...")
        t = threading.Thread(target=self.run_tests, args=(vendor, ip, port, user, password), daemon=True)
        t.start()

    # ------------------------------------------------------------------
    # Lógica principal: conecta via Netmiko e executa os comandos
    # ------------------------------------------------------------------
    def run_tests(self, vendor, ip, port, user, password):
        device_type = DEVICE_TYPES[vendor]
        tunnel = self.tunnel_var.get().strip()
        ping_ip = self.ping_ip_var.get().strip()

        device = {
            "device_type": device_type,
            "host": ip,
            "port": port,
            "username": user,
            "password": password,
            "fast_cli": False,
            "timeout": 160,
        }

        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log("=" * 70, "header")
        self.log(f"Início do teste - {timestamp}", "header")
        self.log(f"Fabricante: {vendor} | Host: {ip}:{port} | Usuário: {user}", "header")
        self.log("=" * 70, "header")

        try:
            self.set_status("Estabelecendo conexão SSH...")
            conn = ConnectHandler(**device)
        except NetmikoAuthenticationException:
            self.log("[ERRO] Falha de autenticação.", "error")
            self._finish()
            return
        except NetmikoTimeoutException:
            self.log("[ERRO] Timeout. Verifique IP, porta e conectividade.", "error")
            self._finish()
            return
        except Exception as exc:
            self.log(f"[ERRO] Falha inesperada ao conectar: {exc}", "error")
            self._finish()
            return

        self.log("[OK] Conexão SSH estabelecida com sucesso.\n", "ok")
        self.set_status("Executando comandos de diagnóstico...")

        try:
            if device_type == "fortinet":
                self._run_fortigate(conn, tunnel, ping_ip)
            else:
                self._run_paloalto(conn, tunnel, ping_ip)
        finally:
            conn.disconnect()

        self.log("\n" + "=" * 70, "header")
        self.log("Resultados obtidos. Analise as saídas acima", "header")
        self.log("=" * 70, "header")
        self._finish()

    def _finish(self):
        self.set_status("Pronto.")
        self.root.after(0, lambda: self.run_btn.config(state="normal"))

    # ------------------------------------------------------------------
    # Execução específica por fabricante
    # ------------------------------------------------------------------
    def _exec_cmd(self, conn, command):
        self.log(f"\n$ {command}", "cmd")
        try:
            output = conn.send_command(command, read_timeout=30)
            if not output.strip():
                output = "(sem saída retornada)"
            self.log(output)
        except Exception as exc:
            self.log(f"[ERRO ao executar comando] {exc}", "error")

    def _run_fortigate(self, conn, tunnel, ping_ip):
        for cmd in FORTIGATE_FIXED_CMDS:
            self._exec_cmd(conn, cmd)

        if tunnel:
            for cmd in FORTIGATE_TUNNEL_CMDS:
                self._exec_cmd(conn, cmd.format(tunnel=tunnel))
        else:
            self.log("\n[INFO] Nome do túnel não informado - pulando comandos específicos.", "header")

        if ping_ip:
            self._exec_cmd(conn, FORTIGATE_PING_CMD.format(ip=ping_ip))
        else:
            self.log("[INFO] IP remoto não informado - pulando teste de ping.", "header")

    def _run_paloalto(self, conn, tunnel, ping_ip):
        for cmd in PALOALTO_FIXED_CMDS:
            self._exec_cmd(conn, cmd)

        if tunnel:
            for cmd in PALOALTO_TUNNEL_CMDS:
                self._exec_cmd(conn, cmd.format(tunnel=tunnel))
        else:
            self.log("\n[INFO] Nome do túnel não informado - pulando comandos específicos.", "header")

        if ping_ip:
            self._exec_cmd(conn, PALOALTO_PING_CMD.format(ip=ping_ip))
        else:
            self.log("[INFO] IP remoto não informado - pulando teste de ping.", "header")


def main():
    root = tk.Tk()
    try:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")
    except Exception:
        pass
    app = VPNTesterApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()