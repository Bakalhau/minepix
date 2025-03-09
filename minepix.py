#!/usr/bin/env python3
import os
import yaml
import json
import logging
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from rcon.source import Client

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('minepix.log')
    ]
)
logger = logging.getLogger('minepix')

# Carregar configuração
def load_config():
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

config = load_config()

# Inicializar app Flask
app = Flask(__name__)

# Autenticação da API LivePix
def get_livepix_token():
    url = "https://oauth.livepix.gg/oauth2/token"
    
    # Obter valores das variáveis de ambiente ou config
    client_id = config['livepix']['client_id']
    client_secret = config['livepix']['client_secret']
    
    payload = {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
        'scope': 'messages:read payments:read'
    }
    
    response = requests.post(url, data=payload)
    if response.status_code == 200:
        return response.json()['access_token']
    else:
        logger.error(f"Falha ao obter token: {response.text}")
        return None

# Função para obter detalhes de pagamento/mensagem da API LivePix
def get_livepix_message(message_id, token):
    url = f"https://api.livepix.gg/v2/messages/{message_id}"
    headers = {
        'Authorization': f'Bearer {token}'
    }
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error(f"Falha ao obter detalhes da mensagem: {response.text}")
        return None

# Função para enviar comando ao servidor Minecraft usando RCON
def send_minecraft_command(command):
    try:
        host = config['minecraft']['host']
        port = int(config['minecraft']['port'])
        password = config['minecraft']['password']
        
        with Client(host, port, passwd=password) as client:
            response = client.run(command)
            logger.info(f"Comando executado: {command}")
            logger.info(f"Resposta: {response}")
            return True
    except Exception as e:
        logger.error(f"Falha ao executar comando: {str(e)}")
        return False

# Encontrar o comando apropriado para o valor da doação
def get_command_for_amount(amount_cents):
    # Recarregar config para garantir que temos a versão mais recente
    try:
        with open('config.yaml', 'r') as f:
            current_config = yaml.safe_load(f)
        commands = current_config['commands']
    except Exception as e:
        logger.error(f"Erro ao recarregar config: {str(e)}")
        commands = config['commands']
    
    # Converter para inteiro para garantir comparação adequada
    amount_cents = int(amount_cents)
    
    # Registrar comandos disponíveis para depuração
    logger.info(f"Comandos disponíveis para valores: {list(commands.keys())}")
    logger.info(f"Procurando comando para o valor: {amount_cents}")
    
    # Encontrar o comando mais próximo que não exceda o valor da doação
    closest_amount = 0
    for cmd_amount_str in sorted([str(a) for a in commands.keys()]):
        cmd_amount = int(cmd_amount_str)
        if cmd_amount <= amount_cents:
            closest_amount = cmd_amount
            logger.info(f"Encontrado comando correspondente para o valor: {closest_amount}")
        else:
            break
    
    # Se encontramos um comando válido
    if closest_amount > 0:
        try:
            # Tentar representações de string e inteiro
            if str(closest_amount) in commands:
                return commands[str(closest_amount)]
            elif closest_amount in commands:
                return commands[closest_amount]
            else:
                logger.error(f"Comando não encontrado para o valor: {closest_amount}")
                # Comando alternativo
                return f"say Doação recebida: {amount_cents/100} BRL"
        except KeyError as e:
            logger.error(f"KeyError: {e} - Chaves disponíveis: {list(commands.keys())}")
            # Comando alternativo se a chave específica estiver ausente
            return f"say Doação recebida: {amount_cents/100} BRL"
    
    # Caso padrão se nenhum comando corresponder
    logger.info(f"Nenhum comando encontrado para o valor: {amount_cents}")
    return "say Obrigado pela sua doação!"

# Formatar o comando com nome do jogador, nome do doador, valor e mensagem
def format_command(command, player, donor, amount, message):
    return command.replace('{player}', player) \
                 .replace('{donor}', donor) \
                 .replace('{amount}', str(amount)) \
                 .replace('{message}', message)

# Manipular webhook de entrada
@app.route('/webhook/<key>/livepix', methods=['POST'])
def webhook_handler(key):
    try:
        # Verificar se a chave é válida
        webhook_key = config['webhook']['key']
        if key != webhook_key:
            logger.warning(f"Chave de webhook inválida: {key}")
            return jsonify({'status': 'error', 'message': 'Chave inválida'}), 403
        
        # Obter dados do webhook
        webhook_data = request.json
        logger.info(f"Webhook recebido: {json.dumps(webhook_data)}")
        
        # Validar dados do webhook
        if not webhook_data or 'resource' not in webhook_data:
            return jsonify({'status': 'error', 'message': 'Dados de webhook inválidos'}), 400
        
        # Verificar se é uma nova mensagem ou pagamento
        if webhook_data['event'] == 'new' and webhook_data['resource']['type'] in ['message', 'payment']:
            resource_id = webhook_data['resource']['id']
            
            # Obter token de autenticação
            token = get_livepix_token()
            if not token:
                logger.error('Falha ao autenticar com a API LivePix')
                # Retornar sucesso apesar do erro para evitar novas tentativas de webhook
                return jsonify({'status': 'success', 'message': 'Webhook recebido mas não foi possível autenticar'}), 200
            
            # Obter os detalhes da mensagem/pagamento
            payment_data = get_livepix_message(resource_id, token)
            if not payment_data or 'data' not in payment_data:
                logger.error('Falha ao obter detalhes do pagamento')
                # Retornar sucesso apesar do erro para evitar novas tentativas de webhook
                return jsonify({'status': 'success', 'message': 'Webhook recebido mas detalhes do pagamento indisponíveis'}), 200
            
            # Extrair informações do pagamento
            data = payment_data['data']
            donor_name = data.get('username', 'Anônimo')
            amount_cents = data.get('amount', 0)
            amount_currency = data.get('currency', 'BRL')
            amount_formatted = f"{amount_cents/100:.2f} {amount_currency}"
            donor_message = data.get('message', '')
            
            # Registrar a doação
            logger.info(f"Doação recebida: {amount_formatted} de {donor_name}: {donor_message}")
            
            # Encontrar o comando apropriado para este valor de doação
            command_template = get_command_for_amount(amount_cents)
            if not command_template:
                logger.info(f"Nenhum comando configurado para o valor: {amount_cents}")
                return jsonify({'status': 'success', 'message': 'Doação recebida mas nenhum comando acionado'}), 200
            
            # Formatar o comando
            player = config['minecraft']['player']
            command = format_command(
                command_template, 
                player,
                donor_name,
                amount_formatted, 
                donor_message
            )
            
            # Enviar comando para Minecraft
            send_result = send_minecraft_command(command)
            if send_result:
                return jsonify({
                    'status': 'success', 
                    'message': 'Doação processada e comando enviado para Minecraft'
                }), 200
            else:
                logger.warning("Falha ao enviar comando para Minecraft mas reconhecendo webhook")
                # Retornar sucesso apesar da falha do RCON para evitar novas tentativas de webhook
                return jsonify({
                    'status': 'success', 
                    'message': 'Doação recebida mas execução do comando falhou'
                }), 200
        
        # Se chegarmos aqui, o webhook foi aceito mas não processado por razões de conteúdo
        return jsonify({'status': 'success', 'message': 'Webhook recebido mas não processado'}), 200
        
    except Exception as e:
        # Capturar quaisquer erros inesperados, registrá-los, mas ainda retornar sucesso
        logger.error(f"Erro inesperado ao processar webhook: {str(e)}")
        return jsonify({'status': 'success', 'message': 'Webhook recebido mas encontrou um erro'}), 200

if __name__ == '__main__':
    # Imprimir a URL do webhook
    port = int(config['webhook']['port'])
    webhook_key = config['webhook']['key']
    
    logger.info("MinePix iniciando...")
    logger.info(f"URL do Webhook: http://seu_ip:{port}/webhook/{webhook_key}/livepix")
    logger.info("Certifique-se de registrar esta URL nas configurações da sua conta LivePix")
    
    # Iniciar o servidor Flask
    app.run(host='0.0.0.0', port=port)