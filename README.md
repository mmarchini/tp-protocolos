# tp-protocolos

Controlador OpenFlow para a topologia de teste do trabalho final da disciplina INF01002 de 2015/1

## Features
 - Desligamento e religamento dos switches 8, 9 e 10 a cada 1 minuto
 - Definição dinâmica da topologia no início da aplicação 
 - Definição do melhor caminho entre cada host através do algoritmo de menor caminho
 - Priorização dos nodos centrais (8, 9 e 10) quando eles estão ligados)

P.S.: Pacotes IPv6 são descartados

## Lógica do controlador

O Controlador é responsável por várias coisas, dentre elas, as principais são:

### Descoberta de melhor caminho

A descoberta do melhor caminho é feito utilizando o algoritmo de shortest path
disponível na biblioteca networkx. Esse algoritmo é aplicado sobre um grafo.
Para gerar o grafo que representa a topologia da rede, foi utilizado o controlador
Switches do Ryu. Esse controlador faz a descoberta da rede utilizando pacotes LLDP.
Após obter a topologia, nosso controlador desabilita o Switches, para evitar flood
de LLDP.

### Alteração da Topologia

A topologia alterna entre dois modos principais: completa e econômica. A completa
abrange todos os switches e links da rede. Já a econômica descarta os switches
8, 9 e 10, e qualquer link que esteja ligado a ele. Essa troca ocorre a cada
um minuto, e quando ela ocorre, todas as regras são apagadas dos switches e
o grafo é desfeito, sendo refeito novamente no próximo PacketIn.

## Instalação

Para instalar o Mininet, basta seguir o tutorial oficial do mesmo.
Para instalar as dependêncais, basta executar:

```bash
$ pip install -r requirements.txt
```

P.S.: O comando acima deve ser executado dentro de um virtualenv (instalação local
das dependências), ou pelo root (instalação global). É necessário ter o pip instalado
para poder executar o comando.

## Preparação

Caso a aplicação for executada em ambiente Linux, é recomendado parar o Network Manager,
pois ele pode interferir na execução:

```bash
$ sudo stop network-manager
```

Também é necessário, antes de cada execução, limpar o mininet:

```bash
$ sudo mn -c 
```

## Execução

Para executar, primeiro devemos iniciar o controlador:

```bash
$ ryu-manager --observe-links ryu_controller
```

Em outro terminal, devemos iniciar o mininet com a sua topologia:

```bash
$ sudo mn --custom topo_script.py --topo evaltopo --switch ovsk --controller remote 
```

