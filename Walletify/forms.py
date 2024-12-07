from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange

class LoginForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class RegistrationForm(FlaskForm):
    username = StringField('Логин', validators=[DataRequired(), Length(min=2, max=20)])
    password = PasswordField('Пароль', validators=[DataRequired()])
    password2 = PasswordField('Повторите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

class TransactionForm(FlaskForm):
    description = StringField('Описание', validators=[DataRequired(), Length(min=1, max=100)])
    amount = FloatField('Сумма', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Сумма должна быть положительной.")
    ])
    category = StringField('Категория', validators=[DataRequired(), Length(min=1, max=50)])
    submit = SubmitField('Добавить транзакцию')

class EditTransactionForm(FlaskForm):
    description = StringField('Описание', validators=[DataRequired(), Length(min=1, max=100)])
    amount = FloatField('Сумма', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Сумма должна быть положительной.")
    ])
    category = StringField('Категория', validators=[DataRequired(), Length(min=1, max=50)])
    submit = SubmitField('Сохранить изменения')

class DepositForm(FlaskForm):
    amount = FloatField('Сумма', validators=[
        DataRequired(),
        NumberRange(min=0.01, message="Сумма должна быть положительной.")
    ])
    submit = SubmitField('Пополнить баланс')