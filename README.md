# MinePix

MinePix é uma aplicação que integra o sistema de doações LivePix com servidores Minecraft, permitindo que doações feitas através da plataforma LivePix acionem comandos automaticamente dentro do jogo. Esta integração cria uma experiência interativa onde os espectadores/doadores podem afetar diretamente o gameplay através de suas doações.

## Funcionalidades

- Recebe webhooks da plataforma LivePix quando novas doações são feitas
- Executa comandos específicos no servidor Minecraft baseados no valor da doação
- Personaliza comandos com informações do doador, valor da doação e mensagem
- Integração segura usando autenticação RCON com o servidor Minecraft
- Sistema configurável de comandos por faixas de valor de doação

## Pré-requisitos

- Python 3.6 ou superior
- Servidor Minecraft com RCON habilitado
- Conta na plataforma LivePix
- Aplicativo/Integração registrado na API LivePix

## Instalação

1. Clone o repositório ou baixe os arquivos
2. Instale as dependências:

```bash
pip install -r requirements.txt
```

3. Copie o arquivo de configuração de exemplo:

```bash
cp config-example.yaml config.yaml
```

4. Edite o arquivo `config.yaml` com suas configurações (veja a seção de Configuração)

## Configuração

Edite o arquivo `config.yaml` com as seguintes informações:

### Configuração da API LivePix

```yaml
livepix:
  client_id: "seu_client_id"    # ID do cliente da sua aplicação LivePix
  client_secret: "seu_secret"    # Secret do cliente da sua aplicação LivePix
```

Para obter essas credenciais, você precisa criar uma aplicação no painel de desenvolvedor da LivePix.

### Configuração do Webhook

```yaml
webhook:
  port: 5000                    # Porta em que o webhook irá escutar
  key: "chave_seguranca"        # Chave de segurança para a URL do webhook
```

A chave de segurança é usada para proteger o endpoint do webhook. Escolha uma string aleatória e complexa.

### Configuração do RCON Minecraft

```yaml
minecraft:
  host: "localhost"             # Endereço do servidor Minecraft
  port: 25575                   # Porta RCON do servidor Minecraft
  password: "senha_rcon"        # Senha do RCON configurada no server.properties
  player: "nome_jogador"        # Nome do jogador que será afetado pelos comandos
```

Você precisa habilitar o RCON no seu servidor Minecraft editando o arquivo `server.properties`:

```
enable-rcon=true
rcon.port=25575
rcon.password=senha_rcon
```

### Configuração dos Comandos

```yaml
commands:
  # R$1,00 = cegueira - 10 segundos
  100: >-
    effect give {player} blindness 10
  # R$5,00 = raio
  500: >-
    execute at {player} run summon lightning_bolt ~ ~ ~
  # R$20,00 = teleportar para o céu
  2000: >-
    execute at {player} run tp ~ ~20 ~
  # ... mais comandos ...
```

Os valores das chaves são em centavos (ex: 100 = R$1,00) e os comandos suportam as seguintes variáveis:

- `{player}`: Nome do jogador configurado em `minecraft.player`
- `{donor}`: Nome do doador da plataforma LivePix
- `{amount}`: Valor da doação formatado
- `{message}`: Mensagem enviada pelo doador

## Executando a Aplicação

```bash
python minepix.py
```

Ao iniciar, a aplicação exibirá a URL do webhook que deve ser configurada na sua conta LivePix:

```
URL do Webhook: http://seu_ip:5000/webhook/chave_seguranca/livepix
```

## Configurando o Webhook no LivePix

1. Acesse sua conta LivePix
2. Vá para as configurações de API e crie uma nova aplicação
3. Copie a secret_key e ID e salve num lugar seguro
4. Configure a URL do webhook exibida ao iniciar o MinePix

## Como Funciona

1. Um espectador faz uma doação através da plataforma LivePix
2. O LivePix envia um webhook para o MinePix
3. O MinePix verifica o valor da doação e seleciona o comando correspondente
4. O comando é formatado com as informações do doador e enviado para o servidor Minecraft via RCON
5. O comando é executado no jogo, afetando o jogador configurado

## Solução de Problemas

Se encontrar problemas, verifique:

- Os logs em `minepix.log` para detalhes sobre erros
- Se as credenciais da API LivePix estão corretas
- Se o RCON está habilitado e configurado corretamente no servidor Minecraft
- Se a URL do webhook está corretamente registrada na LivePix
- Se há firewall bloqueando as conexões na porta configurada

## Considerações de Segurança

- Use uma chave de webhook forte e complexa
- Mantenha seu arquivo `config.yaml` seguro, pois contém senhas
- O RCON não é criptografado, prefira usar em redes locais ou túneis seguros

## Licença

Este projeto é distribuído sob licença GPL-3.
