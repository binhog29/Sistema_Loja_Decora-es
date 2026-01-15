import os
import json
from datetime import datetime, date
from flask import Flask, render_template, request, redirect, url_for, jsonify, session, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Configuração da aplicação Flask
app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui' 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///loja.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Configuração do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Pastas de upload e backup
UPLOAD_FOLDER = 'static/uploads'
CLIENTES_FOLDER = 'static/clientes'
BACKUP_FOLDER = 'backups'

for folder in [UPLOAD_FOLDER, CLIENTES_FOLDER, BACKUP_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# ===== MODELOS DO BANCO DE DADOS =====
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Produto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, default=0)
    tipo = db.Column(db.String(50))
    preco_compra = db.Column(db.Float, default=0.0)
    porcentagem_lucro = db.Column(db.Float, default=0.0)
    preco_venda_aluguel = db.Column(db.Float, default=0.0)
    foto = db.Column(db.String(255))

class Cliente(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20))
    endereco = db.Column(db.String(200))
    coordenadas = db.Column(db.String(50))
    observacao = db.Column(db.Text)
    foto = db.Column(db.String(255))
    transacoes = db.relationship('Transacao', backref='cliente', lazy=True)

class Combo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    observacoes = db.Column(db.Text)
    preco_total = db.Column(db.Float, default=0.0)
    valores_adicionais = db.Column(db.Float, default=0.0)
    itens = db.relationship('ItemCombo', backref='combo', lazy=True, cascade='all, delete-orphan')

class ItemCombo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    combo_id = db.Column(db.Integer, db.ForeignKey('combo.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=False)
    quantidade = db.Column(db.Integer, default=1)
    produto = db.relationship('Produto', backref='itens_combo', lazy=True)

class Transacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cliente_id = db.Column(db.Integer, db.ForeignKey('cliente.id'), nullable=False)
    tipo = db.Column(db.String(50))
    data = db.Column(db.DateTime, default=datetime.now)
    data_inicio = db.Column(db.Date)
    data_fim = db.Column(db.Date)
    frete = db.Column(db.Float, default=0.0)
    desconto = db.Column(db.Float, default=0.0)
    servicos = db.Column(db.Float, default=0.0)
    montagem = db.Column(db.Float, default=0.0)
    forma_pagamento = db.Column(db.String(50))
    total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(50))
    itens = db.relationship('ItemTransacao', backref='transacao', lazy=True, cascade='all, delete-orphan')
    
    @property
    def total_itens(self):
        return sum(item.total_item for item in self.itens)

class ItemTransacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    transacao_id = db.Column(db.Integer, db.ForeignKey('transacao.id'), nullable=False)
    produto_id = db.Column(db.Integer, db.ForeignKey('produto.id'), nullable=True)
    combo_id = db.Column(db.Integer, db.ForeignKey('combo.id'), nullable=True)
    nome = db.Column(db.String(100), nullable=False)
    quantidade = db.Column(db.Integer, default=1)
    preco_unitario = db.Column(db.Float, default=0.0)
    total_item = db.Column(db.Float, default=0.0)

# Funções auxiliares
def formatar_data(d):
    if isinstance(d, date):
        return d.strftime('%Y-%m-%d')
    return d

def formatar_datetime(dt):
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return dt

def carregar_json(arquivo):
    try:
        with open(arquivo, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def salvar_json(dados, arquivo):
    with open(arquivo, 'w') as f:
        json.dump(dados, f, indent=4)

def calcular_preco_final(preco_compra, porcentagem_lucro):
    return preco_compra * (1 + porcentagem_lucro / 100)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Rotas de Autenticação
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('inicio'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Login realizado com sucesso!', 'success')
            return redirect(url_for('inicio'))
        else:
            flash('Usuário ou senha incorretos.', 'danger')
            return render_template('login.html')
            
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu da sua conta.', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Este nome de usuário já está em uso.', 'danger')
            return render_template('register.html')
        else:
            hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
            new_user = User(username=username, password=hashed_password)
            db.session.add(new_user)
            db.session.commit()
            flash('Nova conta criada com sucesso! Faça login para continuar.', 'success')
            return redirect(url_for('login'))
            
    return render_template('register.html')

# Rotas de Navegação e Lógica de Negócio
@app.route('/')
@login_required
def inicio():
    total_vendas_mes = db.session.query(db.func.sum(Transacao.total)).filter(Transacao.tipo == 'Venda', db.func.strftime('%Y-%m', Transacao.data) == datetime.now().strftime('%Y-%m')).scalar() or 0
    total_alugueis_mes = db.session.query(db.func.sum(Transacao.total)).filter(Transacao.tipo == 'Aluguel', db.func.strftime('%Y-%m', Transacao.data) == datetime.now().strftime('%Y-%m')).scalar() or 0
    total_geral_mes = total_vendas_mes + total_alugueis_mes
    
    produtos = Produto.query.all()
    clientes = Cliente.query.all()
    transacoes = Transacao.query.all()

    return render_template('inicio.html', 
                           total_vendas_mes=total_vendas_mes,
                           total_alugueis_mes=total_alugueis_mes,
                           total_geral_mes=total_geral_mes,
                           num_produtos=len(produtos),
                           num_clientes=len(clientes),
                           num_transacoes=len(transacoes))

# Produtos
@app.route('/produtos')
@login_required
def produtos():
    produtos = Produto.query.order_by(Produto.id.desc()).all()
    return render_template('gerenciar_produtos.html', produtos=produtos)

@app.route('/lista_produtos')
@login_required
def lista_produtos():
    produtos = Produto.query.all()
    return render_template('produtos.html', produtos=produtos)

@app.route('/adicionar_produto', methods=['POST'])
@login_required
def adicionar_produto():
    nome = request.form['nome']
    quantidade = int(request.form['quantidade'])
    tipo = request.form['tipo']
    preco_compra = float(request.form['preco_compra'])
    porcentagem_lucro = float(request.form['porcentagem_lucro'])
    
    preco_venda_aluguel = calcular_preco_final(preco_compra, porcentagem_lucro)
    
    foto = None
    if 'foto' in request.files and request.files['foto'].filename != '':
        foto_file = request.files['foto']
        filename = f"{datetime.now().timestamp()}_{foto_file.filename}"
        foto_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        foto = filename

    novo_produto = Produto(nome=nome, quantidade=quantidade, tipo=tipo, preco_compra=preco_compra,
                           porcentagem_lucro=porcentagem_lucro, preco_venda_aluguel=preco_venda_aluguel, foto=foto)
    db.session.add(novo_produto)
    db.session.commit()
    flash("Produto adicionado com sucesso!", "success")
    return redirect(url_for('produtos'))

@app.route('/detalhes_produto/<int:id_produto>')
@login_required
def detalhes_produto(id_produto):
    produto = Produto.query.get_or_404(id_produto)
    return render_template('detalhes_produto.html', produto=produto, id_produto=id_produto)

@app.route('/editar_produto/<int:id_produto>', methods=['GET', 'POST'])
@login_required
def pagina_editar_produto(id_produto):
    produto = Produto.query.get_or_404(id_produto)
    if request.method == 'POST':
        produto.nome = request.form['nome']
        produto.quantidade = int(request.form['quantidade'])
        produto.tipo = request.form['tipo']
        produto.preco_compra = float(request.form['preco_compra'])
        produto.porcentagem_lucro = float(request.form['porcentagem_lucro'])
        produto.preco_venda_aluguel = calcular_preco_final(produto.preco_compra, produto.porcentagem_lucro)

        if 'foto' in request.files and request.files['foto'].filename != '':
            foto_file = request.files['foto']
            filename = f"{datetime.now().timestamp()}_{foto_file.filename}"
            foto_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            produto.foto = filename

        db.session.commit()
        flash("Produto editado com sucesso!", "success")
        return redirect(url_for('produtos'))
    return render_template('editar_produto.html', produto=produto, id_produto=id_produto)

@app.route('/ajustar_estoque', methods=['POST'])
@login_required
def ajustar_estoque():
    id_produto = request.form.get('id_produto')
    quantidade = int(request.form.get('quantidade_ajuste'))
    acao = request.form.get('acao')
    
    produto = Produto.query.get_or_404(id_produto)
    
    if acao == 'adicionar':
        produto.quantidade += quantidade
        flash(f"Estoque de '{produto.nome}' ajustado. Adicionadas {quantidade} unidades.", "success")
    elif acao == 'remover':
        if produto.quantidade < quantidade:
            flash(f"Erro: Não é possível remover mais itens do que o estoque atual de '{produto.nome}'.", "danger")
            return redirect(url_for('produtos'))
        produto.quantidade -= quantidade
        flash(f"Estoque de '{produto.nome}' ajustado. Removidas {quantidade} unidades.", "success")
    
    db.session.commit()
    return redirect(url_for('produtos'))

@app.route('/deletar_produto/<int:id_produto>')
@login_required
def deletar_produto(id_produto):
    produto = Produto.query.get_or_404(id_produto)
    db.session.delete(produto)
    db.session.commit()
    flash("Produto deletado com sucesso.", "warning")
    return redirect(url_for('produtos'))

@app.route('/buscar_produto_ajax')
@login_required
def buscar_produto_ajax():
    termo = request.args.get('termo', '')
    produtos = Produto.query.filter(Produto.nome.ilike(f'%{termo}%')).all()
    
    carrinho = session.get('carrinho', [])
    
    resultados = []
    for produto in produtos:
        estoque_reservado = sum(item['quantidade'] for item in carrinho if item['id'] == produto.id and item['tipo'] == 'produto')
        estoque_disponivel = produto.quantidade - estoque_reservado
        
        resultados.append({
            'id': produto.id,
            'nome': produto.nome,
            'quantidade': estoque_disponivel,
            'preco_venda_aluguel': produto.preco_venda_aluguel
        })
    return jsonify(resultados)

# Clientes
@app.route('/clientes')
@login_required
def clientes():
    clientes = Cliente.query.order_by(Cliente.id.desc()).all()
    return render_template('clientes.html', clientes=clientes)

@app.route('/adicionar_cliente', methods=['POST'])
@login_required
def adicionar_cliente():
    nome = request.form['nome']
    telefone = request.form.get('telefone')
    endereco = request.form.get('endereco')
    coordenadas = request.form.get('coordenadas')
    observacao = request.form.get('observacao')
    
    foto = None
    if 'foto_cliente' in request.files and request.files['foto_cliente'].filename != '':
        foto_file = request.files['foto_cliente']
        filename = f"{datetime.now().timestamp()}_{foto_file.filename}"
        foto_file.save(os.path.join(app.config['CLIENTES_FOLDER'], filename))
        foto = filename
    
    novo_cliente = Cliente(nome=nome, telefone=telefone, endereco=endereco, coordenadas=coordenadas, observacao=observacao, foto=foto)
    db.session.add(novo_cliente)
    db.session.commit()
    flash("Cliente adicionado com sucesso!", "success")
    return redirect(url_for('clientes'))

@app.route('/detalhes_cliente/<int:id_cliente>')
@login_required
def detalhes_cliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    return render_template('detalhes_cliente.html', cliente=cliente, id_cliente=id_cliente)

@app.route('/editar_cliente/<int:id_cliente>', methods=['GET', 'POST'])
@login_required
def pagina_editar_cliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    if request.method == 'POST':
        cliente.nome = request.form['nome']
        cliente.telefone = request.form.get('telefone')
        cliente.endereco = request.form.get('endereco')
        cliente.coordenadas = request.form.get('coordenadas')
        cliente.observacao = request.form.get('observacao')

        if 'foto_cliente' in request.files and request.files['foto_cliente'].filename != '':
            foto_file = request.files['foto_cliente']
            filename = f"{datetime.now().timestamp()}_{foto_file.filename}"
            foto_file.save(os.path.join(app.config['CLIENTES_FOLDER'], filename))
            cliente.foto = filename
        
        db.session.commit()
        flash("Cliente editado com sucesso!", "success")
        return redirect(url_for('clientes'))
    return render_template('editar_cliente.html', cliente=cliente, id_cliente=id_cliente)

@app.route('/deletar_cliente/<int:id_cliente>')
@login_required
def deletar_cliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    db.session.delete(cliente)
    db.session.commit()
    flash("Cliente deletado com sucesso.", "warning")
    return redirect(url_for('clientes'))

# Transações
@app.route('/nova_transacao')
@login_required
def nova_transacao():
    clientes = Cliente.query.order_by(Cliente.nome).all()
    
    if 'carrinho' not in session:
        session['carrinho'] = []
    
    carrinho_detalhes = []
    for item in session['carrinho']:
        if item['tipo'] == 'produto':
            produto = Produto.query.get(item['id'])
            if produto:
                carrinho_detalhes.append({
                    'id': produto.id,
                    'nome': produto.nome,
                    'tipo': 'produto',
                    'quantidade': item['quantidade'],
                    'preco_unitario': produto.preco_venda_aluguel,
                    'total_item': produto.preco_venda_aluguel * item['quantidade'],
                    'estoque_disponivel': produto.quantidade - item['quantidade']
                })
        elif item['tipo'] == 'combo':
            combo = Combo.query.get(item['id'])
            if combo:
                carrinho_detalhes.append({
                    'id': combo.id,
                    'nome': combo.nome,
                    'tipo': 'combo',
                    'quantidade': item['quantidade'],
                    'preco_unitario': combo.preco_total,
                    'total_item': combo.preco_total * item['quantidade']
                })
                
    total_carrinho = sum(item['total_item'] for item in carrinho_detalhes)
    
    return render_template('nova_transacao.html', 
                           clientes=clientes, 
                           carrinho=carrinho_detalhes,
                           total_carrinho=total_carrinho)

@app.route('/transacoes')
@login_required
def historico_transacoes():
    transacoes = Transacao.query.order_by(Transacao.data.desc()).all()
    return render_template('historico_transacoes.html', transacoes=transacoes)

@app.route('/adicionar_ao_carrinho', methods=['POST'])
@login_required
def adicionar_ao_carrinho():
    tipo = request.form['tipo']
    item_id = int(request.form['id'])
    quantidade = int(request.form['quantidade'])
    
    if 'carrinho' not in session:
        session['carrinho'] = []

    carrinho = session['carrinho']
    item_existente = next((item for item in carrinho if item['id'] == item_id and item['tipo'] == tipo), None)
    
    quantidade_atual_no_carrinho = 0
    if item_existente:
        quantidade_atual_no_carrinho = item_existente['quantidade']
    
    quantidade_a_adicionar = quantidade_atual_no_carrinho + quantidade

    if tipo == 'produto':
        produto = Produto.query.get(item_id)
        if not produto or produto.quantidade < quantidade_a_adicionar:
            flash(f"Erro: Estoque insuficiente para o produto '{produto.nome}'. Estoque disponível: {produto.quantidade}.", 'danger')
            return redirect(url_for('nova_transacao'))
    elif tipo == 'combo':
        combo = Combo.query.get(item_id)
        if not combo:
             flash("Erro: Combo não encontrado.", 'danger')
             return redirect(url_for('nova_transacao'))
        for combo_item in combo.itens:
            produto = Produto.query.get(combo_item.produto_id)
            if not produto or produto.quantidade < (combo_item.quantidade * quantidade_a_adicionar):
                 flash(f"Erro: Estoque insuficiente para o produto '{produto.nome}' no combo '{combo.nome}'. Estoque disponível: {produto.quantidade}.", 'danger')
                 return redirect(url_for('nova_transacao'))

    if item_existente:
        item_existente['quantidade'] = quantidade_a_adicionar
    else:
        carrinho.append({'id': item_id, 'tipo': tipo, 'quantidade': quantidade})
    
    session['carrinho'] = carrinho
    flash("Item adicionado ao carrinho com sucesso!", 'success')
    return redirect(url_for('nova_transacao'))

@app.route('/remover_do_carrinho/<string:tipo>/<int:item_id>')
@login_required
def remover_do_carrinho(tipo, item_id):
    if 'carrinho' in session:
        session['carrinho'] = [item for item in session['carrinho'] if not (item['id'] == item_id and item['tipo'] == tipo)]
    flash("Item removido do carrinho.", 'warning')
    return redirect(url_for('nova_transacao'))

@app.route('/finalizar_transacao', methods=['POST'])
@login_required
def finalizar_transacao():
    if not session.get('carrinho'):
        flash("Erro: O carrinho está vazio.", 'danger')
        return redirect(url_for('nova_transacao'))
        
    cliente_id = request.form['cliente_id']
    tipo = request.form['tipo']
    data_inicio = request.form.get('data_inicio')
    data_fim = request.form.get('data_fim')
    frete = float(request.form.get('frete', 0))
    desconto = float(request.form.get('desconto', 0))
    servicos = float(request.form.get('servicos', 0))
    montagem = float(request.form.get('montagem', 0))
    forma_pagamento = request.form['forma_pagamento']
    
    transacao = Transacao(
        cliente_id=cliente_id,
        tipo=tipo,
        data=datetime.now(),
        data_inicio=datetime.strptime(data_inicio, '%Y-%m-%d').date() if data_inicio else None,
        data_fim=datetime.strptime(data_fim, '%Y-%m-%d').date() if data_fim else None,
        frete=frete,
        desconto=desconto,
        servicos=servicos,
        montagem=montagem,
        forma_pagamento=forma_pagamento,
        status='ativo' if tipo == 'Aluguel' else 'finalizado'
    )
    db.session.add(transacao)
    db.session.flush()

    total_itens_calculado = 0
    for item_carrinho in session['carrinho']:
        item_id = item_carrinho['id']
        quantidade = item_carrinho['quantidade']
        tipo_item = item_carrinho['tipo']
        
        if tipo_item == 'produto':
            produto = Produto.query.get(item_id)
            if produto and produto.quantidade >= quantidade:
                item_transacao = ItemTransacao(
                    transacao_id=transacao.id,
                    produto_id=item_id,
                    nome=produto.nome,
                    quantidade=quantidade,
                    preco_unitario=produto.preco_venda_aluguel,
                    total_item=produto.preco_venda_aluguel * quantidade
                )
                db.session.add(item_transacao)
                produto.quantidade -= quantidade
                total_itens_calculado += item_transacao.total_item
            else:
                db.session.rollback()
                flash(f"Erro: Estoque insuficiente para o produto {produto.nome}.", 'danger')
                return redirect(url_for('nova_transacao'))

        elif tipo_item == 'combo':
            combo = Combo.query.get(item_id)
            if combo:
                for combo_item in combo.itens:
                    produto = Produto.query.get(combo_item.produto_id)
                    if produto and produto.quantidade < (combo_item.quantidade * quantidade):
                        db.session.rollback()
                        flash(f"Erro: Estoque insuficiente para o produto '{produto.nome}' no combo '{combo.nome}'.", 'danger')
                        return redirect(url_for('nova_transacao'))
                
                item_transacao = ItemTransacao(
                    transacao_id=transacao.id,
                    combo_id=item_id,
                    nome=combo.nome,
                    quantidade=quantidade,
                    preco_unitario=combo.preco_total,
                    total_item=combo.preco_total * quantidade
                )
                db.session.add(item_transacao)
                
                for combo_item in combo.itens:
                    produto = Produto.query.get(combo_item.produto_id)
                    produto.quantidade -= combo_item.quantidade * quantidade
                total_itens_calculado += item_transacao.total_item
    
    transacao.total = total_itens_calculado + frete + servicos + montagem - desconto
    db.session.commit()
    session.pop('carrinho', None)
    flash("Transação finalizada com sucesso!", 'success')
    return redirect(url_for('comprovante', transacao_id=transacao.id))

# Rota de Orçamento
@app.route('/salvar_orcamento', methods=['POST'])
@login_required
def salvar_orcamento():
    if not session.get('carrinho'):
        flash("Erro: O carrinho está vazio.", 'danger')
        return redirect(url_for('nova_transacao'))

    cliente_id = request.form['cliente_id']
    frete = float(request.form.get('frete', 0))
    desconto = float(request.form.get('desconto', 0))
    servicos = float(request.form.get('servicos', 0))
    montagem = float(request.form.get('montagem', 0))

    orcamento = Transacao(
        cliente_id=cliente_id,
        tipo='Orcamento',
        data=datetime.now(),
        frete=frete,
        desconto=desconto,
        servicos=servicos,
        montagem=montagem,
        forma_pagamento='N/A',
        total=0.0,
        status='orcamento'
    )
    db.session.add(orcamento)
    db.session.flush()

    total_itens_calculado = 0
    for item_carrinho in session['carrinho']:
        item_id = item_carrinho['id']
        quantidade = item_carrinho['quantidade']
        tipo_item = item_carrinho['tipo']

        if tipo_item == 'produto':
            produto = Produto.query.get(item_id)
            if produto:
                item_transacao = ItemTransacao(
                    transacao_id=orcamento.id,
                    produto_id=item_id,
                    nome=produto.nome,
                    quantidade=quantidade,
                    preco_unitario=produto.preco_venda_aluguel,
                    total_item=produto.preco_venda_aluguel * quantidade
                )
                db.session.add(item_transacao)
                total_itens_calculado += item_transacao.total_item

        elif tipo_item == 'combo':
            combo = Combo.query.get(item_id)
            if combo:
                item_transacao = ItemTransacao(
                    transacao_id=orcamento.id,
                    combo_id=item_id,
                    nome=combo.nome,
                    quantidade=quantidade,
                    preco_unitario=combo.preco_total,
                    total_item=combo.preco_total * quantidade
                )
                db.session.add(item_transacao)
                total_itens_calculado += item_transacao.total_item
    
    orcamento.total = total_itens_calculado + frete + servicos + montagem - desconto
    db.session.commit()
    session.pop('carrinho', None)
    flash("Orçamento salvo com sucesso!", 'success')
    return redirect(url_for('comprovante', transacao_id=orcamento.id))

@app.route('/comprovante/<int:transacao_id>')
@login_required
def comprovante(transacao_id):
    transacao = Transacao.query.get_or_404(transacao_id)
    return render_template('comprovante.html', transacao=transacao, cliente=transacao.cliente)

@app.route('/editar_transacao/<int:transacao_id>')
@login_required
def editar_transacao(transacao_id):
    transacao = Transacao.query.get_or_404(transacao_id)
    clientes = Cliente.query.all()
    return render_template('editar_transacao.html', transacao=transacao, clientes=clientes)

@app.route('/salvar_edicao_transacao/<int:transacao_id>', methods=['POST'])
@login_required
def salvar_edicao_transacao(transacao_id):
    transacao = Transacao.query.get_or_404(transacao_id)
    
    transacao.cliente_id = request.form['cliente_id']
    transacao.tipo = request.form['tipo']
    transacao.forma_pagamento = request.form['forma_pagamento']
    transacao.data_inicio = datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date() if request.form.get('data_inicio') else None
    transacao.data_fim = datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date() if request.form.get('data_fim') else None
    transacao.status = request.form['status']
    
    transacao.frete = float(request.form.get('frete', 0))
    transacao.desconto = float(request.form.get('desconto', 0))
    transacao.servicos = float(request.form.get('servicos', 0))
    transacao.montagem = float(request.form.get('montagem', 0))

    total_itens = sum(item.total_item for item in transacao.itens)
    transacao.total = total_itens + transacao.frete + transacao.servicos + transacao.montagem - transacao.desconto

    db.session.commit()
    flash("Transação editada com sucesso!", 'success')
    return redirect(url_for('historico_transacoes'))

@app.route('/finalizar_aluguel/<int:transacao_id>')
@login_required
def finalizar_aluguel(transacao_id):
    transacao = Transacao.query.get_or_404(transacao_id)
    transacao.status = 'finalizado'

    for item in transacao.itens:
        if item.produto_id:
            produto = Produto.query.get(item.produto_id)
            if produto:
                produto.quantidade += item.quantidade
        elif item.combo_id:
            combo = Combo.query.get(item.combo_id)
            for combo_item in combo.itens:
                produto = Produto.query.get(combo_item.produto_id)
                if produto:
                    produto.quantidade += combo_item.quantidade * item.quantidade

    db.session.commit()
    flash("Aluguel finalizado e estoque reposto.", 'success')
    return redirect(url_for('agenda'))

@app.route('/deletar_transacao/<int:transacao_id>')
@login_required
def deletar_transacao(transacao_id):
    transacao = Transacao.query.get_or_404(transacao_id)
    db.session.delete(transacao)
    db.session.commit()
    flash("Transação deletada com sucesso.", 'warning')
    return redirect(url_for('historico_transacoes'))

@app.route('/historico_cliente/<int:id_cliente>')
@login_required
def historico_cliente(id_cliente):
    cliente = Cliente.query.get_or_404(id_cliente)
    historico = Transacao.query.filter_by(cliente_id=id_cliente).order_by(Transacao.data.desc()).all()
    return render_template('historico_cliente.html', cliente=cliente, historico=historico)

# Combos
@app.route('/combos')
@login_required
def combos():
    combos = Combo.query.order_by(Combo.id.desc()).all()
    produtos = Produto.query.all()
    return render_template('combos.html', combos=combos, produtos=produtos)

@app.route('/adicionar_combo', methods=['POST'])
@login_required
def adicionar_combo():
    nome = request.form['nome']
    observacoes = request.form.get('observacoes')
    valores_adicionais = float(request.form.get('valores_adicionais', 0))

    itens_do_combo = []
    preco_base = 0.0

    produtos_ids = request.form.getlist('itens_combo[]')

    for produto_id in produtos_ids:
        quantidade_str = request.form.get(f'quantidade_{produto_id}')
        if quantidade_str:
            quantidade = int(quantidade_str)
            if quantidade > 0:
                produto = Produto.query.get(produto_id)
                if produto:
                    item_combo = ItemCombo(produto_id=produto.id, quantidade=quantidade)
                    itens_do_combo.append(item_combo)
                    preco_base += produto.preco_venda_aluguel * quantidade

    novo_combo = Combo(
        nome=nome,
        observacoes=observacoes,
        valores_adicionais=valores_adicionais,
        preco_total=preco_base + valores_adicionais,
        itens=itens_do_combo
    )
    db.session.add(novo_combo)
    db.session.commit()
    flash("Combo adicionado com sucesso!", 'success')
    return redirect(url_for('combos'))

@app.route('/detalhes_combo/<int:id_combo>')
@login_required
def detalhes_combo(id_combo):
    combo = Combo.query.get_or_404(id_combo)
    itens_detalhados = []
    for item in combo.itens:
        produto = Produto.query.get(item.produto_id)
        if produto:
            itens_detalhados.append({'nome': produto.nome, 'quantidade': item.quantidade, 'id_produto': produto.id})
    return render_template('detalhes_combo.html', combo=combo, id_combo=id_combo, itens_detalhados=itens_detalhados)

@app.route('/editar_combo/<int:id_combo>', methods=['GET', 'POST'])
@login_required
def pagina_editar_combo(id_combo):
    combo = Combo.query.get_or_404(id_combo)
    produtos = Produto.query.all()
    itens_selecionados = {item.produto_id for item in combo.itens}

    if request.method == 'POST':
        combo.nome = request.form['nome']
        combo.observacoes = request.form.get('observacoes')
        combo.valores_adicionais = float(request.form.get('valores_adicionais', 0))
        
        for item in combo.itens:
            db.session.delete(item)
        db.session.commit()

        preco_base = 0.0
        
        produtos_ids = request.form.getlist('itens_combo[]')

        for produto_id in produtos_ids:
            quantidade_str = request.form.get(f'quantidade_{produto_id}')
            if quantidade_str:
                quantidade = int(quantidade_str)
                if quantidade > 0:
                    produto = Produto.query.get(produto_id)
                    if produto:
                        item_combo = ItemCombo(combo_id=combo.id, produto_id=produto.id, quantidade=quantidade)
                        db.session.add(item_combo)
                        preco_base += produto.preco_venda_aluguel * quantidade
        
        combo.preco_total = preco_base + combo.valores_adicionais
        db.session.commit()
        flash("Combo editado com sucesso!", 'success')
        return redirect(url_for('combos'))
        
    return render_template('editar_combo.html', combo=combo, id_combo=id_combo, produtos=produtos, itens_selecionados=itens_selecionados)

@app.route('/deletar_combo/<int:id_combo>')
@login_required
def deletar_combo(id_combo):
    combo = Combo.query.get_or_404(id_combo)
    db.session.delete(combo)
    db.session.commit()
    flash("Combo deletado com sucesso.", 'warning')
    return redirect(url_for('combos'))

@app.route('/buscar_combo_ajax')
@login_required
def buscar_combo_ajax():
    termo = request.args.get('termo', '')
    combos = Combo.query.filter(Combo.nome.ilike(f'%{termo}%')).all()
    
    resultados = []
    for combo in combos:
        resultados.append({
            'id': combo.id,
            'nome': combo.nome,
            'preco_total': combo.preco_total
        })
    return jsonify(resultados)

# Agenda
@app.route('/agenda')
@login_required
def agenda():
    alugueis_ativos = Transacao.query.filter_by(tipo='Aluguel', status='ativo').order_by(Transacao.data_inicio).all()
    alugueis_finalizados = Transacao.query.filter_by(tipo='Aluguel', status='finalizado').order_by(Transacao.data.desc()).all()
    return render_template('agenda.html', alugueis_ativos=alugueis_ativos, alugueis_finalizados=alugueis_finalizados)

# Relatórios
@app.route('/relatorios')
@login_required
def relatorios():
    mes_atual = datetime.now().strftime('%Y-%m')
    
    total_vendas_mes = db.session.query(db.func.sum(Transacao.total)).filter(Transacao.tipo == 'Venda', db.func.strftime('%Y-%m', Transacao.data) == mes_atual).scalar() or 0
    total_alugueis_mes = db.session.query(db.func.sum(Transacao.total)).filter(Transacao.tipo == 'Aluguel', db.func.strftime('%Y-%m', Transacao.data) == mes_atual).scalar() or 0
    total_geral_mes = total_vendas_mes + total_alugueis_mes

    produtos_populares = db.session.query(
        ItemTransacao.nome, 
        db.func.sum(ItemTransacao.quantidade).label('quantidade')
    ).join(Transacao).filter(db.func.strftime('%Y-%m', Transacao.data) == mes_atual).group_by(ItemTransacao.nome).order_by(db.desc('quantidade')).limit(5).all()

    return render_template('relatorios.html', 
                           total_vendas_mes=total_vendas_mes,
                           total_alugueis_mes=total_alugueis_mes,
                           total_geral_mes=total_geral_mes,
                           produtos_populares=produtos_populares)

# Backup e Restauração
@app.route('/backup')
@login_required
def backup():
    agora = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nome_do_arquivo = f'backup_{agora}.json'
    caminho_backup = os.path.join(BACKUP_FOLDER, nome_do_arquivo)
    
    def to_dict(obj):
        return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}

    dados_a_salvar = {
        'produtos': [to_dict(p) for p in Produto.query.all()],
        'clientes': [to_dict(c) for c in Cliente.query.all()],
        'combos': [to_dict(c) for c in Combo.query.all()],
        'transacoes': [to_dict(t) for t in Transacao.query.all()]
    }
    
    salvar_json(dados_a_salvar, caminho_backup)
    
    flash(f"Backup criado com sucesso em: {caminho_backup}", 'success')
    return redirect(url_for('inicio'))

@app.route('/restaurar')
@login_required
def restaurar():
    arquivos_de_backup = [f for f in os.listdir(BACKUP_FOLDER) if f.endswith('.json')]
    return render_template('restaurar.html', backups=arquivos_de_backup)

@app.route('/restaurar_dados/<nome_do_arquivo>')
@login_required
def restaurar_dados(nome_do_arquivo):
    caminho_backup = os.path.join(BACKUP_FOLDER, nome_do_arquivo)
    if not os.path.exists(caminho_backup):
        flash("Erro: Arquivo de backup não encontrado.", 'danger')
        return redirect(url_for('restaurar'))
        
    dados_restaurar = carregar_json(caminho_backup)
    
    db.drop_all()
    db.create_all()

    for p_data in dados_restaurar.get('produtos', []):
        produto = Produto(**p_data)
        db.session.add(produto)
    
    for c_data in dados_restaurar.get('clientes', []):
        cliente = Cliente(**c_data)
        db.session.add(cliente)
        
    for c_data in dados_restaurar.get('combos', []):
        combo = Combo(**c_data)
        db.session.add(combo)
        
    for t_data in dados_restaurar.get('transacoes', []):
        transacao = Transacao(**t_data)
        db.session.add(transacao)

    db.session.commit()
    flash(f"Dados restaurados com sucesso a partir de {nome_do_arquivo}.", 'success')
    return redirect(url_for('inicio'))

@app.route('/limpar_dados')
@login_required
def limpar_dados():
    db.drop_all()
    db.create_all()
    flash("Todos os dados foram apagados e o banco de dados foi reiniciado.", 'warning')
    return redirect(url_for('inicio'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Cria um usuário de teste se não existir
        if not User.query.filter_by(username='admin').first():
            admin_user = User(username='admin', password=generate_password_hash('123', method='pbkdf2:sha256')) 
            db.session.add(admin_user)
            db.session.commit()
    app.run(debug=True)