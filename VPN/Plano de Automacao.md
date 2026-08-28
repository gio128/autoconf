# Plano de Automação — VPN IPSec Site-to-Site entre FortiGate e Palo Alto

## 1. Objetivo

Configurar e validar a criação de um túnel VPN IPSec site-to-site entre um 
firewall **FortiGate** e um firewall **Palo Alto Networks (PAN-OS)**,
garantindo interoperabilidade e velocidade e rapido diagnostico pós-implantação.

---

## 2. Parâmetros da VPN

Todos os parâmetros foram centralizados no APP para ambos os modelos, precisando somente preencher as informações necessárias para configuração.

### 2.1 Endereçamento

| Item | FortiGate (Lado A) | Palo Alto (Lado B) |
|---|---|---|
| IP WAN (peer público) | `172.17.164.113` | `172.17.174.179` |
| Interface WAN | `wan1` | `ethernet1/1` |
| Rede local (LAN) de exemplo | `10.0.0.0/24` | `10.10.0.0/24` |
| Zona de segurança | `ZONA_LAN` | `LAN` |

### 2.2 Rede de túnel (numbered tunnel / VTI)

Uso de uma sub-rede `/30` dedicada para os endpoints do túnel lógico (IPSec baseado em rota
com interface de túnel), permitindo roteamento.

| Item | Valor |
|---|---|
| Rede de túnel | `169.255.1.0/30` |
| IP interno do túnel — FortiGate | `169.255.1.2/30` |
| IP interno do túnel — Palo Alto | `169.255.1.1/30` |
| Interface virtual FortiGate | `TO_SITE` (tipo `ipsec`, modo `tunnel`) |
| Interface virtual Palo Alto | `tunnel.1` |

### 2.3 Proposta de Fase 1 (IKE)

Deve haver **paridade exata** entre os dois fabricantes — qualquer divergência impede a
negociação.

| Parâmetro | Valor acordado |
|---|---|
| Versão IKE | IKEv2 |
| Modo de autenticação | Pre-shared key (PSK) — recomenda-se migrar para certificados em produção |
| Algoritmo de criptografia | AES-256-CBC (ou AES-256-GCM se ambos suportarem) |
| Hash / Integridade | SHA-256 |
| Grupo Diffie-Hellman | Grupo 14 (2048-bit) |
| Lifetime da Fase 1 | 28800 segundos (8h) |
| DPD (Dead Peer Detection) | Habilitado, intervalo 10s, retry 3x |
| NAT-Traversal | Habilitado (auto-detecção) |

### 2.4 Proposta de Fase 2 (IPSec / Quick Mode)

| Parâmetro | Valor acordado |
|---|---|
| Protocolo | ESP |
| Algoritmo de criptografia | AES-256-CBC |
| Hash / Integridade | SHA-256  |
| PFS (Perfect Forward Secrecy) | Habilitado — Grupo DH 14 |
| Lifetime da Fase 2 | 3600 segundos |
| Seletores de tráfego (Proxy-ID) | Em modo route-based, usar `0.0.0.0/0 <-> 0.0.0.0/0` |

---

## 3. Ferramentas e APIs

| Dispositivo | Opção primária | Opção alternativa |
|---|---|---|
| FortiGate | **FortiOS REST API** (`/api/v2/cmdb/...`, `/api/v2/monitor/...`), autenticação via token de API ou sessão HTTPS | SSH + CLI scripting (biblioteca `netmiko` / `paramiko`); FortiManager API para gerenciamento centralizado em escala |
| Palo Alto | **PAN-OS XML API** (`/api/?type=config&action=set...`) via biblioteca `pan-os-python` (antigo `pandevice`) | REST API do PAN-OS (a partir da versão 10.x); Panorama API para gerenciamento centralizado |
| Orquestração | Python 3.11+, com `requests`, `pan-os-python`, `PyYAML`, `tenacity` (retries) | Ansible com coleções `fortinet.fortios` e `paloaltonetworks.panos` |
| Validação/monitoramento | APIs de *monitor* (FortiOS) e *op commands* (PAN-OS `<show><vpn>...`) | SNMP, Syslog centralizado (ex: FortiAnalyzer / Panorama / SIEM) |
| Versionamento e CI/CD | Git + pipeline (GitHub Actions/GitLab CI) para aplicar e validar automaticamente | — |

---

## 4. Passos lógicos de automação

O script/pipeline segue a mesma sequência conceitual nos dois fabricantes, adaptando a sintaxe
de cada API.

### 4.1 Pré-requisitos
1. Carregar parâmetros de `configs/params.yaml` (IPs, PSK — via *secret store*/vault, nunca em
   texto puro no repositório, propostas de Fase 1/2, redes locais).
2. Autenticar em ambos os dispositivos (token/API key do FortiGate; `api_key` do PAN-OS).
3. Validar conectividade de gerenciamento (HTTPS) com ambos antes de qualquer alteração.

### 4.2 FortiGate
1. Criar/validar objeto de endereço da LAN remota (`firewall address`).
2. Criar a fase 1 (`vpn ipsec phase1-interface`): peer IP, interface WAN, PSK, propostas IKE,
   modo `route-based` (interface dedicada), DPD, NAT-T.
3. Criar a fase 2 (`vpn ipsec phase2-interface`): vincular à fase 1, propostas ESP, PFS,
   seletores `0.0.0.0/0`.
4. Configurar a interface de túnel resultante com o IP `169.255.1.1/30`.
5. Criar rota estática apontando a rede remota (`10.10.0.0/24`) para a interface de túnel.
6. Criar políticas de firewall (*policy*) bidirecionais entre a zona `internal` e a interface de
   túnel, permitindo os serviços necessários (ou `ALL` em ambiente de teste).
7. Habilitar NAT=disable nas políticas do túnel (tráfego intra-VPN não deve ser mascarado).

### 4.3 Palo Alto
1. Criar objeto de endereço da LAN remota em Address Objects.
2. Criar o **IKE Crypto Profile** com as propostas de Fase 1 acordadas.
3. Criar o **IPSec Crypto Profile** com as propostas de Fase 2 acordadas.
4. Criar o **IKE Gateway**: peer IP, interface local, PSK, versão IKEv2, perfil IKE Crypto.
5. Criar a **Tunnel Interface** (`tunnel.1`) com o IP `169.255.1.2/30`, associada a uma zona
   de VPN dedicada (ex: `vpn-zone`).
6. Criar o **IPSec Tunnel**: vincular IKE Gateway + IPSec Crypto Profile + Tunnel Interface.
7. Criar rota estática na *virtual router* apontando a rede remota (`10.0.0.0/24`) para
   `tunnel.1`.
8. Criar regras de segurança (*Security Policy*) entre a zona `LAN` e a zona `ZONA_VPN`
   (e vice-versa).
9. Garantir que **não exista NAT Policy** aplicada ao tráfego destinado à rede remota via túnel.
10. Executar `commit` via API e verificar o *job status* até conclusão.

### 4.4 Pós-configuração (ambos)
1. Aguardar a negociação (ou forçar via API/CLI).
2. Executar rotina de validação (seção 6).

---

## 5. Considerações específicas de automação cross-vendor

- **Nomenclatura e modelos de objeto distintos**: FortiGate usa uma configuração "plana"
  (CLI/API orientada a comandos sequenciais); PAN-OS usa uma árvore XML hierárquica
  (`vsys > network > tunnel`, `vsys > network > ike`, etc.). O código de automação precisa de
  camadas de abstração separadas por fabricante, não um único "template genérico".
- **Terminologia equivalente, mas não idêntica**: "Phase 1/Phase 2" (Fortinet) vs.
  "IKE Gateway / IPSec Tunnel" (Palo Alto); "interface-based VPN" (Fortinet) vs. "tunnel
  interface numerada" (Palo Alto) — a automação deve mapear conceitos, não nomes.
- **Ordem de criação de dependências**: no PAN-OS, a Tunnel Interface deve existir e estar
  associada a uma zona *antes* de ser referenciada pelo IPSec Tunnel; no FortiGate a interface
  de túnel é criada automaticamente junto com a Phase1. A automação precisa respeitar a ordem
  correta de cada API (criação de objeto → perfis → gateway/phase1 → tunnel/phase2 → rota →
  política).
- **Compatibilidade de algoritmos por versão de firmware**: nem toda combinação de
  criptografia/hash/DH está disponível nas duas plataformas ao mesmo tempo (ex: suporte a
  AES-GCM ou grupos ECP variam por versão de FortiOS/PAN-OS). O script deve validar a versão
  do firmware antes de aplicar propostas mais recentes.
- **PSK e segredos**: nunca versionar a chave pré-compartilhada em texto claro no Git. Utilizar
  variáveis de ambiente, Vault (HashiCorp), ou *secrets* do pipeline de CI/CD.
- **Idempotência**: reaplicar o script não deve duplicar objetos. Isso exige checar existência
  (`GET`) antes de `POST`/`SET`, ou usar operações "set"/"upsert" quando a API suportar.
- **Rollback**: como cada fabricante trata transações de forma diferente (FortiGate não tem
  rollback nativo via API simples; PAN-OS permite `revert config` antes do commit), a
  automação deve implementar rollback próprio: capturar o estado anterior (`GET` de
  configuração) antes de qualquer alteração, para restaurar em caso de falha.
- **Relógio (NTP) e certificados**: divergências de horário entre os equipamentos podem causar
  falhas de autenticação/DPD; validar sincronização NTP antes de habilitar o túnel.

---

## 6. Validação de configuração e alertas

### 6.1 Verificação de configuração aplicada

| Verificação | FortiGate | Palo Alto |
|---|---|---|
| Fase 1/IKE Gateway existe e está correta | "show vpn ipsec phase1-interface" | "show network ike gateway" |
| Fase 2/IPSec Tunnel existe e está correta | "show vpn ipsec phase2-interface" | "show network tunnel ipsec IPSEC-VPN1" |
| Rota estática presente | "show router static {ID ROTA}" | "show network virtual-router default routing-table ip static-route {ROUTE_VPN}" |
| Política de firewall presente | "show firewall policy {ID POLICY VPN}" | "show rulebase security rules To-VPN" |

### 6.2 Verificação do estado do túnel

| Verificação | FortiGate | Palo Alto |
|---|---|---|
| Status da Fase 1 (SA estabelecida) | "diagnose vpn ike gateway list" | "show vpn ike-sa" |
| Status da Fase 2 (SA ativa) | "diagnose vpn tunnel list" | "show vpn ipsec-sa" |
| Contadores de bytes/pacotes no túnel | "get vpn ipsec tunnel summary" | "show vpn tunnel" |
| Teste de conectividade fim a fim | Ping ao IP interno do túnel remoto (`IP LAN`) a partir do FortiGate | Ping ao IP interno do túnel remoto (`IP LAN`) a partir do Palo Alto |
| Teste de conectividade entre LANs | Ping/traceroute de host em `10.10.0.0/24` para host em `10.0.0.0/24` | idem, sentido inverso |

O script `conf_vpn.py` executa as checagens e comandos da sequência de configuração.  

No repositorio, encontra-se prints e scripts destas duas ferramentas:
- vpn_conf.py > Gerador de script de configuração VPN
- vpntester.py > Aplicativo que realiza verificação de VPN nos Fortigates e Palo Alto
