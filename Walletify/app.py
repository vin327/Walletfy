from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from forms import TransactionForm, DepositForm, LoginForm, RegistrationForm, EditTransactionForm
from models import db, Transaction, User, Balance
import logging

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'  # Замените на секретный ключ
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///finance.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/')
def index():
    if current_user.is_authenticated:
        balance = Balance.query.filter_by(user_id=current_user.id).first()
        if balance is None:
            balance = Balance(user_id=current_user.id)
            db.session.add(balance)
            db.session.commit()
        transactions = Transaction.query.filter_by(user_id=current_user.id).all()
        return render_template('index.html', balance=balance.amount, transactions=transactions)
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user:
            flash('Этот логин уже занят')
            return redirect(url_for('register'))
        hashed_password = generate_password_hash(form.password.data)
        if form.username.data.lower() == 'admin':
            user = User(username=form.username.data, password_hash=hashed_password, is_admin=True)
        else:
            user = User(username=form.username.data, password_hash=hashed_password)
        db.session.add(user)
        db.session.commit()
        balance = Balance(user_id=user.id)
        db.session.add(balance)
        db.session.commit()
        flash('Регистрация успешна!')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and check_password_hash(user.password_hash, form.password.data):
            login_user(user)
            flash('Добро пожаловать!')
            return redirect(url_for('index'))
        flash('Неверный логин или пароль')
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.')
    return redirect(url_for('index'))


@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_transaction():
    form = TransactionForm()
    if form.validate_on_submit():
        balance = Balance.query.filter_by(user_id=current_user.id).first()
        amount = float(form.amount.data)
        if balance.amount < amount:
            flash('Недостаточно средств на балансе')
            return redirect(url_for('add_transaction'))
        transaction = Transaction(
            description=form.description.data,
            amount=amount,
            category=form.category.data,
            user_id=current_user.id
        )
        balance.amount -= amount
        db.session.add(transaction)
        db.session.commit()
        flash('Транзакция успешно добавлена!')
        return redirect(url_for('index'))
    return render_template('add_transaction.html', form=form)


@app.route('/deposit', methods=['GET', 'POST'])
@login_required
def deposit():
    form = DepositForm()
    balance = Balance.query.filter_by(user_id=current_user.id).first()
    if form.validate_on_submit():
        balance.amount += form.amount.data
        db.session.commit()
        flash('Баланс успешно пополнен!')
        return redirect(url_for('index'))
    return render_template('deposit.html', form=form, balance=balance.amount)


@app.route('/transactions')
@login_required
def transactions():
    transactions = Transaction.query.filter_by(user_id=current_user.id).all()
    return render_template('transactions.html', transactions=transactions)


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    if not current_user.is_admin:
        flash('У вас нет доступа к административной панели.')
        return redirect(url_for('index'))
    transactions = Transaction.query.all()
    return render_template('admin.html', transactions=transactions)


@app.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    if not current_user.is_admin:
        logging.warning(f"Пользователь {current_user.username} попытался редактировать транзакцию без прав.")
        flash('У вас нет прав для редактирования транзакций.', 'danger')
        return redirect(url_for('index'))
    transaction = Transaction.query.get(transaction_id)
    if transaction is None:
        logging.error(f"Транзакция с ID {transaction_id} не найдена.")
        flash('Транзакция не найдена.', 'danger')
        return redirect(url_for('admin'))
    logging.info(f"Администратор {current_user.username} редактирует транзакцию ID {transaction_id}.")
    form = EditTransactionForm(obj=transaction)
    form = EditTransactionForm(obj=transaction)
    if form.validate_on_submit():
        try:
            # Восстановление предыдущего баланса
            balance = Balance.query.filter_by(user_id=transaction.user_id).first()
            balance.amount += transaction.amount  # Возврат старой суммы

            new_amount = float(form.amount.data)
            if balance.amount < new_amount:
                flash('Недостаточно средств для изменения суммы транзакции.', 'danger')
                return render_template('edit_transaction.html', form=form, transaction=transaction)

            transaction.description = form.description.data
            transaction.amount = new_amount
            transaction.category = form.category.data
            balance.amount -= new_amount  # Вычитание новой суммы
            db.session.commit()
            flash('Транзакция успешно изменена!', 'success')
            return redirect(url_for('admin'))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при изменении транзакции: {e}', 'danger')
    return render_template('edit_transaction.html', form=form, transaction=transaction)

@app.route('/delete/<int:transaction_id>')
@login_required
def delete_transaction(transaction_id):
    if not current_user.is_admin:
        flash('У вас нет прав для удаления транзакций.', 'danger')
        return redirect(url_for('index'))
    transaction = Transaction.query.get(transaction_id)
    if transaction is None:
        flash('Транзакция не найдена.', 'danger')
        return redirect(url_for('admin'))
    try:
        balance = Balance.query.filter_by(user_id=transaction.user_id).first()
        balance.amount += transaction.amount  # Возврат суммы транзакции при удалении

        db.session.delete(transaction)
        db.session.commit()
        flash('Транзакция успешно удалена!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении транзакции: {e}', 'danger')
    return redirect(url_for('admin'))

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html')


def init_db():
    user = User.query.filter_by(username='admin').first()
    if not user:
        hashed_password = generate_password_hash('admin')
        user = User(username='admin', password_hash=hashed_password, is_admin=True)
        db.session.add(user)
        db.session.commit()
        balance = Balance(user_id=user.id)
        db.session.add(balance)
        db.session.commit()


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_db()  # вызов функции init_db
    app.run(debug=True)