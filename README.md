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

