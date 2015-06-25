# tp-protocolos

Controlador OpenFlow para a topologia de teste do trabalho final da disciplina INF01002 de 2015/1

Features: 
 - Desligamento e religamento dos switches 8, 9 e 10 a cada 1 minuto
 - Definição do melhor caminho entre cada host através do algoritmo de menor caminho

P.S.: Pacotes IPv6 são descartados


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
$ ryu-manager ryu_controller
```

Em outro terminal, devemos iniciar o mininet com a sua topologia:

```bash
$ sudo mn --custom topo_script.py --topo evaltopo --switch ovsk --controller remote 
```

