#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog


# ---------------------------------------------------------------------------
# Estilo / helpers
# ---------------------------------------------------------------------------

PAD = 6


def add_label_entry(parent, row, label_text, default="", width=32, show=None):
    """Cria um Label + Entry na linha 'row' de um grid e retorna o widget Entry."""
    lbl = ttk.Label(parent, text=label_text)
    lbl.grid(row=row, column=0, sticky="w", padx=PAD, pady=3)
    var = tk.StringVar(value=default)
    entry = ttk.Entry(parent, textvariable=var, width=width, show=show)
    entry.grid(row=row, column=1, sticky="we", padx=PAD, pady=3)
    return var


def add_label_combo(parent, row, label_text, values, default=None, width=29):
    lbl = ttk.Label(parent, text=label_text)
    lbl.grid(row=row, column=0, sticky="w", padx=PAD, pady=3)
    var = tk.StringVar(value=default if default else values[0])
    combo = ttk.Combobox(parent, textvariable=var, values=values, width=width, state="readonly")
    combo.grid(row=row, column=1, sticky="we", padx=PAD, pady=3)
    return var


# ---------------------------------------------------------------------------
# Aplicação principal
# ---------------------------------------------------------------------------

class VPNGeneratorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gerador de Scripts VPN - Fortigate / Palo Alto")
        self.geometry("780x760")
        self.minsize(720, 640)

        self.vendor = tk.StringVar(value="")

        self._build_vendor_selector()

        # Container onde os formulários (Fortigate ou Palo Alto) serão desenhados
        self.form_container = ttk.Frame(self)
        self.form_container.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.fortigate_frame = None
        self.paloalto_frame = None

        self._build_action_buttons()
        self._build_output_area()

        # Nenhum fabricante selecionado inicialmente -> nenhum formulário visível
        self._show_placeholder()

    # ------------------------------------------------------------------
    # Seletor de fabricante
    # ------------------------------------------------------------------
    def _build_vendor_selector(self):
        top = ttk.LabelFrame(self, text="1. Selecione o equipamento")
        top.pack(fill="x", padx=10, pady=10)

        ttk.Radiobutton(
            top, text="Fortigate", variable=self.vendor, value="fortigate",
            command=self._on_vendor_change
        ).pack(side="left", padx=15, pady=8)

        ttk.Radiobutton(
            top, text="Palo Alto", variable=self.vendor, value="paloalto",
            command=self._on_vendor_change
        ).pack(side="left", padx=15, pady=8)

    def _on_vendor_change(self):
        # Limpa o container de formulário
        for child in self.form_container.winfo_children():
            child.pack_forget()

        if self.vendor.get() == "fortigate":
            if self.fortigate_frame is None:
                self.fortigate_frame = self._build_fortigate_form(self.form_container)
            self.fortigate_frame.pack(fill="both", expand=True)
        elif self.vendor.get() == "paloalto":
            if self.paloalto_frame is None:
                self.paloalto_frame = self._build_paloalto_form(self.form_container)
            self.paloalto_frame.pack(fill="both", expand=True)

    @staticmethod
    def _bind_mousewheel(canvas):
        """Permite rolar o formulário com a roda do mouse quando o cursor está sobre ele."""
        def _on_mousewheel(event):
            delta = -1 * (event.delta // 120) if event.delta else 0
            if event.num == 4:  # Linux scroll up
                delta = -1
            elif event.num == 5:  # Linux scroll down
                delta = 1
            canvas.yview_scroll(delta, "units")

        canvas.bind("<Enter>", lambda e: (
            canvas.bind_all("<MouseWheel>", _on_mousewheel),
            canvas.bind_all("<Button-4>", _on_mousewheel),
            canvas.bind_all("<Button-5>", _on_mousewheel),
        ))
        canvas.bind("<Leave>", lambda e: (
            canvas.unbind_all("<MouseWheel>"),
            canvas.unbind_all("<Button-4>"),
            canvas.unbind_all("<Button-5>"),
        ))

    def _show_placeholder(self):
        self.placeholder = ttk.Label(
            self.form_container,
            text="Selecione um fabricante para habilitar os campos de configuração.",
            foreground="#666"
        )
        self.placeholder.pack(pady=40)

    # ------------------------------------------------------------------
    # Formulário FORTIGATE
    # ------------------------------------------------------------------
    def _build_fortigate_form(self, parent):
        # Canvas + scrollbar para permitir rolagem caso a janela seja pequena
        wrapper = ttk.Frame(parent)

        canvas = tk.Canvas(wrapper, highlightthickness=0)
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)

        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(canvas)

        self.fg = {}
        r = 0

        # --- Fase 1 (IKE) ---
        box1 = ttk.LabelFrame(frame, text="Fase 1 - IKE (phase1-interface)")
        box1.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box1.columnconfigure(1, weight=1)
        r += 1

        self.fg["tunnel_name"] = add_label_entry(box1, 0, "Nome do túnel:", "TO_SITE02")
        self.fg["interface"] = add_label_entry(box1, 1, "Interface local (WAN):", "port1")
        self.fg["ike_version"] = add_label_combo(box1, 2, "Versão IKE:", ["1", "2"], "2")
        self.fg["keylife"] = add_label_entry(box1, 3, "Keylife (segundos):", "28800")
        self.fg["proposal_p1"] = add_label_entry(box1, 4, "Proposal (fase 1):", "des-sha1")
        self.fg["dhgrp_p1"] = add_label_entry(box1, 5, "DH Group (fase 1):", "14")
        self.fg["remote_gw"] = add_label_entry(box1, 6, "IP do gateway remoto:", "0.0.0.0")
        self.fg["psksecret"] = add_label_entry(box1, 7, "Chave pré-compartilhada (PSK):", "", show="*")

        # --- Fase 2 (IPSec) ---
        box2 = ttk.LabelFrame(frame, text="Fase 2 - IPSec (phase2-interface)")
        box2.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box2.columnconfigure(1, weight=1)
        r += 1

        self.fg["proposal_p2"] = add_label_entry(box2, 0, "Proposal (fase 2):", "des-sha1")
        self.fg["dhgrp_p2"] = add_label_entry(box2, 1, "DH Group (fase 2):", "14")
        self.fg["keylifeseconds"] = add_label_entry(box2, 2, "Keylife seconds:", "3600")
        self.fg["src_subnet"] = add_label_entry(box2, 3, "Sub-rede local (src-subnet):", "10.0.0.0 255.255.255.0")
        self.fg["dst_subnet"] = add_label_entry(box2, 4, "Sub-rede remota (dst-subnet):", "10.10.0.0 255.255.255.0")

        # --- Interface de túnel ---
        box3 = ttk.LabelFrame(frame, text="Interface de túnel (system interface)")
        box3.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box3.columnconfigure(1, weight=1)
        r += 1

        self.fg["vdom"] = add_label_entry(box3, 0, "VDOM:", "root")
        self.fg["local_tunnel_ip"] = add_label_entry(box3, 1, "IP local do túnel:", "169.255.1.2 255.255.255.255")
        self.fg["remote_tunnel_ip"] = add_label_entry(box3, 2, "IP remoto do túnel:", "169.255.1.1 255.255.255.252")
        self.fg["allowaccess"] = add_label_entry(box3, 3, "Allow access:", "ping")

        # --- Roteamento estático ---
        box4 = ttk.LabelFrame(frame, text="Rota estática (router static)")
        box4.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box4.columnconfigure(1, weight=1)
        r += 1

        self.fg["route_id"] = add_label_entry(box4, 0, "ID da rota:", "2")
        self.fg["route_dst"] = add_label_entry(box4, 1, "Destino da rota:", "10.10.0.0 255.255.255.0")

        # --- Políticas de firewall ---
        box5 = ttk.LabelFrame(frame, text="Políticas de firewall (firewall policy)")
        box5.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box5.columnconfigure(1, weight=1)
        r += 1

        self.fg["zona_lan"] = add_label_entry(box5, 0, "Zona/Interface LAN:", "ZONA_LAN")
        self.fg["zona_vpn"] = add_label_entry(box5, 1, "Zona/Interface VPN:", "ZONA_VPN")
        self.fg["lan_subnet"] = add_label_entry(box5, 2, "Sub-rede LAN (CIDR):", "10.0.0.0/24")
        self.fg["remote_subnet_cidr"] = add_label_entry(box5, 3, "Sub-rede remota (CIDR):", "10.10.0.0/24")
        self.fg["service"] = add_label_entry(box5, 4, "Serviço:", "ALL")

        ttk.Button(
            frame, text="Gerar Script Fortigate", command=self.generate_fortigate
        ).grid(row=r, column=0, pady=12)

        return wrapper

    # ------------------------------------------------------------------
    # Formulário PALO ALTO
    # ------------------------------------------------------------------
    def _build_paloalto_form(self, parent):
        wrapper = ttk.Frame(parent)

        canvas = tk.Canvas(wrapper, highlightthickness=0)
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
        frame = ttk.Frame(canvas)

        frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self._bind_mousewheel(canvas)

        self.pa = {}
        r = 0

        # --- Zona ---
        box0 = ttk.LabelFrame(frame, text="Zona")
        box0.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box0.columnconfigure(1, weight=1)
        r += 1
        self.pa["zone_vpn"] = add_label_entry(box0, 0, "Nome da zona VPN:", "ZONA_VPN")

        # --- Perfis de criptografia ---
        box1 = ttk.LabelFrame(frame, text="Perfis de criptografia (IKE / IPSec)")
        box1.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box1.columnconfigure(1, weight=1)
        r += 1

        self.pa["ike_profile_name"] = add_label_entry(box1, 0, "Nome do perfil IKE:", "IKE-VPN1")
        self.pa["ike_dhgroup"] = add_label_entry(box1, 1, "DH Group (IKE):", "group14")
        self.pa["ike_encryption"] = add_label_entry(box1, 2, "Encriptação (IKE):", "aes-256-gcm")
        self.pa["ike_auth"] = add_label_entry(box1, 3, "Autenticação (IKE):", "sha1")
        self.pa["ike_lifetime"] = add_label_entry(box1, 4, "Lifetime IKE (s):", "28800")

        self.pa["ipsec_profile_name"] = add_label_entry(box1, 5, "Nome do perfil IPSec:", "IPSec-VPN1")
        self.pa["ipsec_encryption"] = add_label_entry(box1, 6, "Encriptação (IPSec):", "aes-256-gcm")
        self.pa["ipsec_auth"] = add_label_entry(box1, 7, "Autenticação (IPSec):", "sha1")
        self.pa["ipsec_lifetime"] = add_label_entry(box1, 8, "Lifetime IPSec (s):", "3600")
        self.pa["ipsec_dhgroup"] = add_label_entry(box1, 9, "DH Group (IPSec):", "group14")

        # --- Interface de túnel ---
        box2 = ttk.LabelFrame(frame, text="Interface de túnel")
        box2.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box2.columnconfigure(1, weight=1)
        r += 1

        self.pa["tunnel_if_name"] = add_label_entry(box2, 0, "Nome da interface de túnel:", "tunnel.1")
        self.pa["tunnel_if_ip"] = add_label_entry(box2, 1, "IP da interface de túnel:", "169.255.1.1/30")

        # --- Gateway IKE ---
        box3 = ttk.LabelFrame(frame, text="Gateway IKE")
        box3.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box3.columnconfigure(1, weight=1)
        r += 1

        self.pa["ike_gw_name"] = add_label_entry(box3, 0, "Nome do gateway IKE:", "IKE-GW-VPN1")
        self.pa["psk"] = add_label_entry(box3, 1, "Chave pré-compartilhada (PSK):", "", show="*")
        self.pa["ike_version"] = add_label_combo(box3, 2, "Versão IKE:", ["ikev1", "ikev2"], "ikev2")
        self.pa["local_interface"] = add_label_entry(box3, 3, "Interface local (WAN):", "ethernet1/2")
        self.pa["local_ip"] = add_label_entry(box3, 4, "IP local (WAN, com máscara):", "172.17.174.179/20")
        self.pa["peer_ip"] = add_label_entry(box3, 5, "IP do peer remoto:", "0.0.0.0")

        # --- Túnel IPSec ---
        box4 = ttk.LabelFrame(frame, text="Túnel IPSec")
        box4.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box4.columnconfigure(1, weight=1)
        r += 1

        self.pa["ipsec_tunnel_name"] = add_label_entry(box4, 0, "Nome do túnel IPSec:", "IPSEC-VPN1")
        self.pa["proxy_id_name"] = add_label_entry(box4, 1, "Nome do Proxy-ID:", "LAN-to-VPN")
        self.pa["proxy_local"] = add_label_entry(box4, 2, "Sub-rede local (proxy-id):", "10.10.0.0/24")
        self.pa["proxy_remote"] = add_label_entry(box4, 3, "Sub-rede remota (proxy-id):", "10.0.0.0/24")

        # --- Roteamento ---
        box5 = ttk.LabelFrame(frame, text="Rota estática")
        box5.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box5.columnconfigure(1, weight=1)
        r += 1

        self.pa["route_name"] = add_label_entry(box5, 0, "Nome da rota:", "ROTA_VPN")
        self.pa["route_dst"] = add_label_entry(box5, 1, "Destino da rota (CIDR):", "10.0.0.0/24")

        # --- Regras de segurança ---
        box6 = ttk.LabelFrame(frame, text="Regras de segurança (rulebase)")
        box6.grid(row=r, column=0, sticky="we", padx=8, pady=6)
        box6.columnconfigure(1, weight=1)
        r += 1

        self.pa["zone_lan"] = add_label_entry(box6, 0, "Zona LAN:", "ZONA_LAN")
        self.pa["rule_to_vpn"] = add_label_entry(box6, 1, "Nome regra LAN->VPN:", "To-VPN")
        self.pa["rule_from_vpn"] = add_label_entry(box6, 2, "Nome regra VPN->LAN:", "VPN-to-LAN")
        self.pa["src_lan"] = add_label_entry(box6, 3, "Origem (LAN, CIDR):", "10.10.0.0/24")
        self.pa["dst_remote"] = add_label_entry(box6, 4, "Destino (remoto, CIDR):", "10.0.0.0/24")

        ttk.Button(
            frame, text="Gerar Script Palo Alto", command=self.generate_paloalto
        ).grid(row=r, column=0, pady=12)

        return wrapper

    # ------------------------------------------------------------------
    # Botões de ação e área de saída
    # ------------------------------------------------------------------
    def _build_action_buttons(self):
        pass  # os botões "Gerar Script" ficam dentro de cada formulário

    def _build_output_area(self):
        out_frame = ttk.LabelFrame(self, text="2. Script gerado")
        out_frame.pack(fill="both", expand=False, padx=10, pady=(0, 10))

        self.output_text = tk.Text(out_frame, height=14, wrap="none", font=("Courier New", 10))
        self.output_text.pack(fill="both", expand=True, side="left", padx=(6, 0), pady=6)

        yscroll = ttk.Scrollbar(out_frame, orient="vertical", command=self.output_text.yview)
        yscroll.pack(side="right", fill="y")
        self.output_text.configure(yscrollcommand=yscroll.set)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Button(btn_frame, text="Salvar script em arquivo...", command=self._save_script).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Copiar para área de transferência", command=self._copy_script).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Limpar", command=self._clear_output).pack(side="left", padx=4)

    def _set_output(self, text):
        self.output_text.delete("1.0", tk.END)
        self.output_text.insert(tk.END, text)

    def _clear_output(self):
        self.output_text.delete("1.0", tk.END)

    def _save_script(self):
        content = self.output_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("Aviso", "Não há script gerado para salvar.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Arquivo de texto", "*.txt"), ("Todos os arquivos", "*.*")],
            initialfile="script_vpn.txt"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content + "\n")
            messagebox.showinfo("Sucesso", f"Script salvo em:\n{path}")

    def _copy_script(self):
        content = self.output_text.get("1.0", tk.END).strip()
        if not content:
            messagebox.showwarning("Aviso", "Não há script gerado para copiar.")
            return
        self.clipboard_clear()
        self.clipboard_append(content)
        messagebox.showinfo("Copiado", "Script copiado para a área de transferência.")

    # ------------------------------------------------------------------
    # Validação simples
    # ------------------------------------------------------------------
    @staticmethod
    def _required(fields_dict, keys, labels):
        """Verifica se os campos obrigatórios foram preenchidos. Retorna lista de erros."""
        errors = []
        for k, lbl in zip(keys, labels):
            if not fields_dict[k].get().strip():
                errors.append(lbl)
        return errors

    # ------------------------------------------------------------------
    # Geração do script FORTIGATE
    # ------------------------------------------------------------------
    def generate_fortigate(self):
        f = self.fg

        required_keys = ["tunnel_name", "interface", "remote_gw", "psksecret",
                          "src_subnet", "dst_subnet", "local_tunnel_ip", "remote_tunnel_ip",
                          "route_dst", "lan_subnet", "remote_subnet_cidr"]
        required_labels = ["Nome do túnel", "Interface local", "IP do gateway remoto",
                            "Chave pré-compartilhada", "Sub-rede local (fase 2)",
                            "Sub-rede remota (fase 2)", "IP local do túnel", "IP remoto do túnel",
                            "Destino da rota", "Sub-rede LAN", "Sub-rede remota (CIDR)"]
        missing = self._required(f, required_keys, required_labels)
        if missing:
            messagebox.showerror("Campos obrigatórios", "Preencha os seguintes campos:\n- " + "\n- ".join(missing))
            return

        tunnel = f["tunnel_name"].get().strip()

        script = f'''config vpn ipsec phase1-interface
    edit "{tunnel}"
        set interface "{f["interface"].get().strip()}"
        set ike-version {f["ike_version"].get().strip()}
        set keylife {f["keylife"].get().strip()}
        set peertype any
        set net-device disable
        set proposal {f["proposal_p1"].get().strip()}
        set dhgrp {f["dhgrp_p1"].get().strip()}
        set remote-gw {f["remote_gw"].get().strip()}
        set psksecret {f["psksecret"].get().strip()}
    next
end

config vpn ipsec phase2-interface
    edit "{tunnel}"
        set phase1name "{tunnel}"
        set proposal {f["proposal_p2"].get().strip()}
        set dhgrp {f["dhgrp_p2"].get().strip()}
        set auto-negotiate enable
        set keylifeseconds {f["keylifeseconds"].get().strip()}
        set src-subnet {f["src_subnet"].get().strip()}
        set dst-subnet {f["dst_subnet"].get().strip()}
    next
end

config system interface
    edit "{tunnel}"
        set vdom "{f["vdom"].get().strip()}"
        set ip {f["local_tunnel_ip"].get().strip()}
        set allowaccess {f["allowaccess"].get().strip()}
        set type tunnel
        set remote-ip {f["remote_tunnel_ip"].get().strip()}
        set interface "{f["interface"].get().strip()}"
    next
end

config router static
    edit {f["route_id"].get().strip()}
        set dst {f["route_dst"].get().strip()}
        set device "{tunnel}"
    next
end

config firewall policy
    edit 0
        set name "TO_TUNNEL"
        set srcintf "{f["zona_lan"].get().strip()}"
        set dstintf "{f["zona_vpn"].get().strip()}"
        set action accept
        set srcaddr "{f["lan_subnet"].get().strip()}"
        set dstaddr "{f["remote_subnet_cidr"].get().strip()}"
        set schedule "always"
        set service "{f["service"].get().strip()}"
        set logtraffic all
    next
    edit 0
        set name "FROM_TUNNEL"
        set srcintf "{f["zona_vpn"].get().strip()}"
        set dstintf "{f["zona_lan"].get().strip()}"
        set action accept
        set srcaddr "{f["remote_subnet_cidr"].get().strip()}"
        set dstaddr "{f["lan_subnet"].get().strip()}"
        set schedule "always"
        set service "{f["service"].get().strip()}"
        set logtraffic all
    next
end
'''
        self._set_output(script)

    # ------------------------------------------------------------------
    # Geração do script PALO ALTO
    # ------------------------------------------------------------------
    def generate_paloalto(self):
        p = self.pa

        required_keys = ["ike_gw_name", "psk", "local_interface", "local_ip", "peer_ip",
                          "tunnel_if_ip", "proxy_local", "proxy_remote", "route_dst",
                          "src_lan", "dst_remote"]
        required_labels = ["Nome do gateway IKE", "Chave pré-compartilhada", "Interface local",
                            "IP local (WAN)", "IP do peer remoto", "IP da interface de túnel",
                            "Sub-rede local (proxy-id)", "Sub-rede remota (proxy-id)",
                            "Destino da rota", "Origem (LAN)", "Destino (remoto)"]
        missing = self._required(p, required_keys, required_labels)
        if missing:
            messagebox.showerror("Campos obrigatórios", "Preencha os seguintes campos:\n- " + "\n- ".join(missing))
            return

        script = f'''configure

set zone {p["zone_vpn"].get().strip()} network layer3

set network ike crypto-profiles ike-crypto-profile {p["ike_profile_name"].get().strip()} dh-group {p["ike_dhgroup"].get().strip()} encryption {p["ike_encryption"].get().strip()} authentication {p["ike_auth"].get().strip()} lifetime {p["ike_lifetime"].get().strip()}
set network ike crypto-profiles ipsec-crypto-profile {p["ipsec_profile_name"].get().strip()} esp encryption {p["ipsec_encryption"].get().strip()} authentication {p["ipsec_auth"].get().strip()} lifetime {p["ipsec_lifetime"].get().strip()} dh-group {p["ipsec_dhgroup"].get().strip()}

set network interface tunnel {p["tunnel_if_name"].get().strip()} ip {p["tunnel_if_ip"].get().strip()}
set network interface tunnel {p["tunnel_if_name"].get().strip()} zone {p["zone_vpn"].get().strip()}

set network ike gateway {p["ike_gw_name"].get().strip()} authentication pre-shared-key {p["psk"].get().strip()}
set network ike gateway {p["ike_gw_name"].get().strip()} version {p["ike_version"].get().strip()}
set network ike gateway {p["ike_gw_name"].get().strip()} ike-crypto-profile {p["ike_profile_name"].get().strip()}
set network ike gateway {p["ike_gw_name"].get().strip()} local-address interface {p["local_interface"].get().strip()} ip {p["local_ip"].get().strip()}
set network ike gateway {p["ike_gw_name"].get().strip()} protocol-common nat-traversal
set network ike gateway {p["ike_gw_name"].get().strip()} peer-address ip {p["peer_ip"].get().strip()}

set network tunnel ipsec {p["ipsec_tunnel_name"].get().strip()} tunnel-interface {p["tunnel_if_name"].get().strip()}
set network tunnel ipsec {p["ipsec_tunnel_name"].get().strip()} auto-key ike-gateway {p["ike_gw_name"].get().strip()}
set network tunnel ipsec {p["ipsec_tunnel_name"].get().strip()} auto-key ipsec-crypto-profile {p["ipsec_profile_name"].get().strip()}
set network tunnel ipsec {p["ipsec_tunnel_name"].get().strip()} auto-key proxy-id {p["proxy_id_name"].get().strip()} local {p["proxy_local"].get().strip()} remote {p["proxy_remote"].get().strip()} protocol any

set network virtual-router default routing-table ip static-route {p["route_name"].get().strip()} destination {p["route_dst"].get().strip()} interface {p["tunnel_if_name"].get().strip()}

set rulebase security rules {p["rule_to_vpn"].get().strip()} from {p["zone_lan"].get().strip()} to {p["zone_vpn"].get().strip()} source {p["src_lan"].get().strip()} destination {p["dst_remote"].get().strip()} application any action allow
set rulebase security rules {p["rule_from_vpn"].get().strip()} from {p["zone_vpn"].get().strip()} to {p["zone_lan"].get().strip()} source {p["dst_remote"].get().strip()} destination {p["src_lan"].get().strip()} application any action allow

commit
'''
        self._set_output(script)


if __name__ == "__main__":
    app = VPNGeneratorApp()
    app.mainloop()