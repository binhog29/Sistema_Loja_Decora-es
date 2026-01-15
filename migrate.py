import os
import json
from datetime import datetime, date
from app import app, db, Produto, Cliente, Transacao, Combo, ItemTransacao, ItemCombo

# Função para carregar dados de um arquivo JSON
def carregar_json(arquivo):
    try:
        with open(arquivo, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Aviso: Arquivo '{arquivo}' não encontrado. Iniciando com dados vazios.")
        return {}
    except json.JSONDecodeError:
        print(f"Erro: Arquivo '{arquivo}' está mal formatado. Por favor, verifique-o.")
        return {}

def migrate_data():
    with app.app_context():
        print("Migrando dados dos arquivos JSON para o banco de dados...")
        
        # Limpa o banco de dados antes de começar
        db.drop_all()
        db.create_all()
        
        # Dicionários para armazenar objetos criados e suas chaves
        # Isso evita que o SQLAlchemy tente criar IDs duplicados
        produtos_migrados = {}
        clientes_migrados = {}
        combos_migrados = {}

        # Migrar Produtos
        produtos_json = carregar_json('produtos.json')
        for id_str, p_data in produtos_json.items():
            produto = Produto(
                id=int(id_str),
                nome=p_data['nome'],
                quantidade=p_data['quantidade'],
                tipo=p_data.get('tipo', 'N/A'),
                preco_compra=p_data.get('preco_compra', 0.0),
                porcentagem_lucro=p_data.get('porcentagem_lucro', 0.0),
                preco_venda_aluguel=p_data.get('preco_venda_aluguel', 0.0),
                foto=p_data.get('foto')
            )
            db.session.add(produto)
            produtos_migrados[int(id_str)] = produto
        db.session.commit()
        print("Produtos migrados.")
        
        # Migrar Clientes
        clientes_json = carregar_json('clientes.json')
        for id_str, c_data in clientes_json.items():
            cliente = Cliente(
                id=int(id_str),
                nome=c_data['nome'],
                telefone=c_data.get('telefone'),
                endereco=c_data.get('endereco'),
                coordenadas=c_data.get('coordenadas'),
                observacao=c_data.get('observacao'),
                foto=c_data.get('foto')
            )
            db.session.add(cliente)
            clientes_migrados[int(id_str)] = cliente
        db.session.commit()
        print("Clientes migrados.")

        # Migrar Combos
        combos_json = carregar_json('combos.json')
        for id_str, c_data in combos_json.items():
            combo = Combo(
                id=int(id_str),
                nome=c_data['nome'],
                observacoes=c_data.get('observacoes'),
                preco_total=c_data.get('preco_total', 0.0),
                valores_adicionais=c_data.get('valores_adicionais', 0.0)
            )
            db.session.add(combo)
            combos_migrados[int(id_str)] = combo
        db.session.commit()

        # Migrar Itens de Combo (depende dos Produtos e Combos)
        for id_str, c_data in combos_json.items():
            if c_data.get('itens'):
                for item in c_data.get('itens', []):
                    item_combo = ItemCombo(
                        combo_id=int(id_str),
                        produto_id=int(item['id_produto']),
                        quantidade=item['quantidade']
                    )
                    db.session.add(item_combo)
        db.session.commit()
        print("Combos e seus itens migrados.")

        # Migrar Transações (depende dos Clientes)
        transacoes_json = carregar_json('transacoes.json')
        for id_str, t_data in transacoes_json.items():
            # Converte as strings de data para objetos date/datetime
            data_inicio_obj = datetime.strptime(t_data['data_inicio'], '%Y-%m-%d').date() if t_data.get('data_inicio') else None
            data_fim_obj = datetime.strptime(t_data['data_fim'], '%Y-%m-%d').date() if t_data.get('data_fim') else None
            data_transacao_obj = datetime.fromisoformat(t_data['data']) if t_data.get('data') else datetime.now()

            transacao = Transacao(
                id=int(id_str),
                cliente_id=int(t_data['id_cliente']),
                tipo=t_data['tipo'],
                data=data_transacao_obj,
                data_inicio=data_inicio_obj,
                data_fim=data_fim_obj,
                frete=t_data.get('frete', 0.0),
                desconto=t_data.get('desconto', 0.0),
                servicos=t_data.get('servicos', 0.0),
                montagem=t_data.get('montagem', 0.0),
                forma_pagamento=t_data.get('forma_pagamento'),
                total=t_data.get('total', 0.0),
                status=t_data.get('status')
            )
            db.session.add(transacao)
            db.session.flush() # Salva a transação para que o ID seja gerado

            # Migrar Itens da Transação (depende da Transação principal)
            for item in t_data.get('itens', []):
                item_transacao = ItemTransacao(
                    transacao_id=transacao.id,
                    produto_id=int(item['id_produto']) if item.get('id_produto') else None,
                    combo_id=int(item['id_combo']) if item.get('id_combo') else None,
                    nome=item['nome'],
                    quantidade=item['quantidade'],
                    preco_unitario=item['preco_unitario'],
                    total_item=item['total_item']
                )
                db.session.add(item_transacao)

        db.session.commit()
        print("Transações e seus itens migrados.")
        print("Migração concluída com sucesso!")

if __name__ == '__main__':
    migrate_data()
