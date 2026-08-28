Automação de Configuração e Testes de Redes  

Projeto desenvolvido para automatizar processos de configuração, validação e testes em ambientes de redes e segurança. As aplicações têm como objetivo reduzir tarefas manuais, padronizar configurações e aumentar a eficiência na administração de infraestrutura.  

Principais funcionalidades  
Automação de switches Cisco: configuração automatizada de equipamentos, aplicação de parâmetros de rede e padronização de configurações.  
Configuração automatizada de VPN: criação e parametrização de túneis VPN, facilitando a implantação de conexões seguras.  
Testes de VPN em firewalls: validação de conectividade e funcionamento dos túneis VPN em ambientes FortiGate e Palo Alto Networks.  
Validação de configurações: execução de testes para verificar conectividade, status dos túneis e funcionamento dos serviços configurados.  
Padronização e redução de tarefas manuais: utilização de automação para tornar os processos mais rápidos, consistentes e menos suscetíveis a erros humanos.  

O projeto integra conceitos de automação de redes, gerenciamento de dispositivos, segurança da informação, VPN e administração de firewalls, proporcionando uma abordagem mais eficiente para implantação e validação de infraestrutura de redes.

Estrutura do repositório

```
gio128/autoconf
├── VPN/                                 <- Diretorio dos aplicativos VPN
│   ├── AMBIENTE GNS3.PNG                <- Print do ambiente simulado.
│   ├── FWs CONECTADOS.PNG               <- Print dos Firewalls conectados após configuração no ambiente simulado.
│   ├── PRINT APP VPN CONFIG.PNG         <- Print do aplicativo gerador de script de configuração VPN (Fortigate e Palo Alto)
│   ├── PRINT APP VPN TESTER.PNG         <- Print do aplicativo testador de VPN estabelecida (Fortigate e Palo Alto)
│   ├── Plano de Automacao.md            <- Documentação sobre o Projeto de Automação VPN
│   ├── SCRIPT VPN - PALO ALTO.txt       <- Script de configuração de VPN IPSec modelo (Palo Alto)
│   ├── SCRIPT VPN FGT.txt               <- Script de configuração de VPN IPSec modelo (Fortigate)
│   ├── conf_vpn.py                      <- Aplicativo para geração de script de configuração VPN Fortigate ou Palo Alto
│   └── vpntester.py                     <- Aplicativo para testes e diagnosticos de VPN IPSec Fortigate e Palo Alto
├── OUTPUT-AUTO-CONF.txt                 <- Saida do aplicativo configurador de switch Cisco
├── OUTPUT-BKP.txt                       <- Saida do aplicativo configurador de switch Cisco, usando recurso backup
├── OUTPUT-VALIDACAOF.txt                <- Saida do aplicativo configurador de switch Cisco, usando recurso validação
├── PRINT APLICATIVO.PNG                 <- Print do aplicativo configurador de switch Cisco em execução
├── SW-AUTOCONF-01_20260827_180142.cfg   <- Bakcup do Switch Cisco configurado
├── conf_sw.py                           <- Aplicativo para configuração de switch em Python
├── template.py                          <- Template da configuração a ser aplicada no switch pelo aplicativo
└── README.md                            <- este documento
```

Configurador de Switch Cisco 

Aplicação desktop (GUI) para automatizar a configuração de switches Cisco, com três funções principais:  

O que faz?  
Configuração automática – aplica um template de comandos (hostname, VLANs, etc.)  
Validação – Confere as configurações aplicadas.  
Backup – salva a configuração atual de três formas: arquivo local, envio TFTP ou envio para um repositório GitHub (via Git).  

Linguagem e bibliotecas

Python 3.  
tkinter – interface gráfica.  
netmiko – conexão e automação Telnet/SSH com dispositivos de rede.  
subprocess – execução de comandos Git.  
os / datetime / threading / logging – utilitários para sistema, timestamps, concorrência e registro de logs.  

Requisitos para uso

Python 3.6+ instalado.  
Pacotes Python: netmiko, tkinter (geralmente incluso no Windows).  
Arquivo template.py no mesmo diretório, contendo as listas CONFIG_COMMANDS e VLAN_COMMANDS.  
Acesso Telnet ao switch (IP, porta, usuário/senha).  
Para backup TFTP – servidor TFTP acessível.  
Para backup GitHub – Git instalado e configurado; repositório local clonado com remoto origin configurado; permissões de commit/push.  

Funcionamento

Interface com campos editáveis (IP, credenciais, servidores).  
Operações executadas em threads separadas, mantendo a GUI responsiva.  
Toda saída de comandos e mensagens são exibidas em uma área de rolagem.  

Backup do switch configurado neste repositório: SW-AUTOCONF-01_20260827_180142.cfg 
