from flask import Flask, redirect, render_template, request
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
import sqlalchemy

from data import db_session
from data.users import User
from data.games import Games
from data.login_form import LoginForm
from data.register_form import RegistrationForm
from data.delete_form import DeleteForm
from data.search_form import SearchForm
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.is_submitted():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.login == form.login.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html',
                               message="Неправильный логин или пароль",
                               form=form, title='Авторизация')
    return render_template('login.html', title='Авторизация', form=form)


@app.route('/')
def index():
    return render_template('index.html', title='Игра панорама')


@app.route('/edit/<int:user_id>', methods=['GET', 'POST'])
def edit(user_id):
    if current_user.is_authenticated and current_user._get_current_object().is_admin:
        form = RegistrationForm()
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == user_id).first()
        if not form.is_submitted():
            form.login.data = user.login
            form.nickname.data = user.nickname
            form.rating.data = user.rating
            form.matches_number.data = user.matches_number
        else:
            user.login = form.login.data
            user.nickname = form.nickname.data
            user.rating = form.rating.data
            user.matches_number = form.matches_number.data
            if form.password.data:
                user.set_password(form.password.data)
            db_sess.add(user)
            db_sess.commit()
            return redirect('/admin/0')
        return render_template('edit.html', title='Редактирование', form=form)
    else:
        return 'Вы не администратор!'


@app.route('/delete/<int:user_id>', methods=['GET', 'POST'])
def delete(user_id):
    if current_user.is_authenticated and current_user._get_current_object().is_admin:
        form = DeleteForm()
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.id == user_id).first()
        if not user:
            form.confirm.errors = ('Пользователь уже удален',)
        if user and form.is_submitted():
            if str(form.confirm.data) == form.confirm.label.text:
                db_sess.delete(user)
                db_sess.commit()
                return redirect('/admin/0')
            else:
                form.confirm.errors = ('Числа не совпадают',)
        return render_template('delete.html', title='Удаление', user=user, form=form)
    else:
        return 'Вы не администратор!'


@app.route('/admin')
def admin_():
    return redirect('/admin/0')


@app.route('/admin/<int:page_number>', methods=['GET', 'POST'])
def admin(page_number=0):
    if current_user.is_authenticated and current_user._get_current_object().is_admin:
        form = SearchForm()
        if request.method == 'POST':
            if form.login or form.nickname or form.rating or form.matches_number:
                if not form.rating.data:
                    search_rating = ''
                else:
                    search_rating = str(form.rating.data)
                if not form.matches_number.data:
                    search_matches_number = ''
                else:
                    search_matches_number = str(form.matches_number.data)
                rating_list = []
                for user in player_top.global_top_player:
                    if (form.login.data in user[3] and
                        form.nickname.data in user[0] and
                            search_rating in user[1] and
                            search_matches_number in user[2]):
                        rating_list.append(user)
            else:
                rating_list = player_top.global_top_player[20 * page_number:20 * (page_number + 1)]
        else:
            rating_list = player_top.global_top_player[20 * page_number:20 * (page_number + 1)]

        return render_template('admin.html',
                               rating_list=rating_list,
                               page_number=page_number,
                               max_page_number=player_top.global_top_player_len // 20 +
                                               bool(player_top.global_top_player_len % 20), title='админка', form=form)
    else:
        return 'Вы не администратор!'


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.is_submitted():
        db_sess = db_session.create_session()
        user = User()
        user.nickname = form.nickname.data
        user.login = form.login.data
        if form.password.data:
            user.set_password(form.password.data)
        else:
            form.login.errors = ('Пароль не может быть пустым',)
            return render_template('register.html', title='Регистрация', form=form)
        if form.password.data == form.repeat_password.data:
            user.set_password(form.password.data)
        else:
            form.repeat_password.errors = ('Пароли должны совпадать',)
            return render_template('register.html', title='Регистрация', form=form)

        db_sess.add(user)
        try:
            db_sess.commit()
        except sqlalchemy.exc.IntegrityError as e:
            if 'user.login' in str(e):
                form.login.errors = ('Пользователь с таким логином существует',)
            return render_template('register.html', title='Регистрация', form=form)
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/not_authenticated')
def not_authenticated():
    return render_template('not_authenticated.html', title='Не авторизирован')


@app.route('/personal_page', methods=['GET', 'POST'])
def personal_page():
    if not current_user.is_authenticated:
        return redirect('/not_authenticated')
    else:
        nickname = current_user.nickname
        login = current_user.login
        matches_number = current_user.matches_number
        rating = current_user.rating
        db_sess = db_session.create_session()
        user_game_list = db_sess.query(Games).filter(Games.user_id == current_user.id)
        if len(list(user_game_list)) > 20:
            user_game_list = user_game_list[:20]
        return render_template('personal_page.html', nickname=nickname,
                               login=login, matches_number=matches_number, rating=rating, current_user=current_user,
                               user_game_list=user_game_list, title='Личная информация')


@app.route('/global_rating')
def rating_():
    return redirect('/global_rating/0')


@app.route('/global_rating/<int:page_number>')
def rating(page_number=0):
    return render_template('rating.html',
                           rating_list=[(nickname, raitng, matches_number) for nickname, raitng, matches_number, _, _ in
                                        player_top.global_top_player[20 * page_number:20 * (page_number + 1)]],
                           page_number=page_number,
                           max_page_number=player_top.global_top_player_len // 20 +
                                           bool(player_top.global_top_player_len % 20), title='Рейтинг')


@app.route('/game', methods=['GET', 'POST'])
def game():
    a = [('52.65', '90.08333'), ('53.71667', '91.41667'), ('53.68333', '53.65'), ('44.86667', '38.16667'), ('55.9', '53.93333'), ('56.51667', '52.98333'), ('44.884525', '39.19202'), ('54.85', '53.06667'), ('47.1', '39.41667'), ('51.16667', '90.6'), ('47.26667', '39.86667'), ('43.04167', '44.21056'), ('57.85', '61.7'), ('54.85', '46.58333'), ('58.6', '125.38333'), ('52.5', '82.78333'), ('56.39361', '38.715'), ('50.9', '142.15'), ('59.16667', '57.58333'), ('50.63', '38.68639'), ('54.5', '37.06667'), ('55.55', '98.66667'), ('44.41972', '34.04306'), ('44.66722', '34.39778'), ('54.9', '52.3'), ('50.21667', '136.9'), ('64.73333', '177.51667'), ('44.89444', '37.31667'), ('52.56667', '103.91667'), ('56.65', '32.26667'), ('56.08333', '86.03333'), ('46.71667', '142.51667'), ('67.5675', '33.39333'), ('55.53333', '37.05'), ('44.46083', '39.74056'), ('56.7', '60.83333'), ('43.29444', '45.88389'), ('54.85', '46.23333'), ('43.17278', '44.29222'), ('55.38333', '43.8'), ('51.93333', '43.5'), ('45', '41.11667'), ('46.10694', '33.69306'), ('44.16667', '133.26667'), ('56.09056', '49.87639'), ('43.35', '132.18333'), ('54.35', '93.43333'), ('57.33639', '61.89194'), ('64.55', '40.53333'), ('57.01027679', '61.45639038'), ('57', '86.15'), ('46.33333', '48.03333'), ('51.86667', '45'), ('48.28333', '46.16667'), ('56.26667', '90.5'), ('55', '57.25'), ('59.38333', '35.95'), ('51.71667', '105.86667'), ('54.4', '53.25'), ('54.38333', '20.63333'), ('51.51722', '104.15611'), ('52.58333', '58.31667'), ('54.93333', '58.8'), ('43.683333', '43.533333'), ('55.18333', '36.65'), ('52.03333', '47.78333'), ('56.48083', '43.54028'), ('55.8', '37.93333'), ('51.55', '43.16667'), ('51.57694', '116.64917'), ('54.65', '19.91667'), ('55.35', '78.35'), ('53.347361', '83.77833'), ('53.65', '47.11667'), ('47.13333', '39.75'), ('44.75278', '33.86083'), ('57.78333', '36.7'), ('48.17472', '40.79306'), ('58.83333', '50.85'), ('50.6', '36.6'), ('54.1', '54.13333'), ('52.96667', '43.41667'), ('54.41667', '86.3'), ('50.91667', '128.48333'), ('45.05444', '34.60222'), ('60.03333', '37.78333'), ('52', '84.98333'), ('64.51667', '34.76667'), ('55.46139', '38.44222'), ('53.96667', '58.4'), ('44.76667', '39.86667'), ('55.09167', '36.66667'), ('63.71667', '66.66667'), ('55.83333', '32.93333'), ('53.8', '36.13333'), ('54.75', '83.1'), ('59.40806', '56.80528'), ('55.66667', '86.25'), ('56.9', '60.8'), ('43.18889', '44.521691'), ('52.51667', '85.16667'), ('46.81667', '134.25'), ('68.05', '166.45'), ('48.78333', '132.93333'), ('55.41667', '55.53333'), ('55.95', '97.81667'), ('50.65', '38.4'), ('50.25778', '127.53639'), ('55.03333', '55.98333'), ('45.1029039', '43.4251513'), ('51.09444', '40.03222'), ('56.78333', '62.05'), ('53.76667', '38.13333'), ('56.09972', '43.50722'), ('56.2', '89.51667'), ('49.93333', '40.55'), ('57.85', '114.2'), ('59.47333', '33.84806'), ('54.96667', '49.03333'), ('57.87083', '34.07361'), ('55.66667', '84.4'), ('54.08333', '37.81667'), ('53.45', '36'), ('43.11667', '132.35'), ('56.36028', '44.05917'), ('50.38333', '116.53333'), ('51.36667', '42.08333'), ('58.38694', '33.91139'), ('55.2', '36.48333'), ('55.9', '94.9'), ('56.11667', '101.6'), ('55.42278', '38.25889'), ('53.25', '34.36667'), ('54.53333', '52.78333'), ('53.61667', '52.41667'), ('44.79', '44.14'), ('52.76667', '52.26667'), ('54.96667', '48.28333'), ('58.48333', '41.51667'), ('42.81667', '47.11667'), ('50.825', '40.58889'), ('57.96667', '33.25'), ('50.18333', '38.11667'), ('55.6', '31.2'), ('56.35', '30.51667'), ('58.525', '31.275'), ('60.75889', '46.30389'), ('61.06667', '42.1'), ('54.35', '38.26667'), ('58.06667', '54.65'), ('55.33333', '36.18333'), ('53.88333', '59.21667'), ('57.38333', '59.93333'), ('56.05', '60.23333'), ('56.96667', '60.58333'), ('58.05', '60.55'), ('58.3574333', '59.8224444'), ('58.86667', '60.8'), ('67.55', '133.38333'), ('58.65', '37.26667'), ('57.85556', '45.78111'), ('55.55', '37.7'), ('63.75', '121.61667'), ('52.93333', '158.4'), ('56.11667', '101.16667'), ('57.2', '41.91667'), ('43.11667', '131.9'), ('43.01667', '44.683315'), ('56.13333', '40.41667'), ('48.71167', '44.51389'), ('47.54', '42.20722'), ('57.43333', '41.16667'), ('55.86667', '48.35'), ('48.78333', '44.76667'), ('59.21667', '39.9'), ('56.23333', '43.2'), ('56.03333', '35.95'), ('59.45', '29.48333'), ('59.91667', '32.35'), ('59.93333', '60.05'), ('52.05', '47.38333'), ('67.5', '64.03333'), ('51.67167', '39.21056'), ('55.98333', '43.26667'), ('55.32333', '38.68056'), ('57.05', '54'), ('60.01667', '30.65'), ('63.86667', '57.31667'), ('60.70917', '28.74417'), ('55.31944', '42.17306'), ('56.31667', '36.55'), ('60.61667', '28.56667'), ('61', '36.45'), ('57.58333', '34.56667'), ('47.53333', '134.75'), ('56.24333', '42.12917'), ('55.21028', '34.285'), ('56.218417', '51.068583'), ('56.56667', '40.11667'), ('57.3', '39.85'), ('55.55', '35'), ('69.25528', '33.31667'), ('51.46667', '58.45'), ('58.38333', '42.35'), ('59.56667', '30.13333'), ('54.65', '21.06667'), ('58.73333', '27.81667'), ('44.56083', '38.07667'), ('44.15', '43.46667'), ('58.14083', '52.67417'), ('55.61472', '36.98722'), ('56.13333', '43.06667'), ('51.96', '85.96'), ('58.38333', '58.31667'), ('50.993028', '81.467934'), ('56.65028', '43.47028'), ('53.26667', '45.7'), ('46.08333', '41.93333'), ('56.20278', '42.6925'), ('44.63333', '39.13333'), ('50.48333', '35.66667'), ('58.56667', '57.83333'), ('43.31667', '45.7'), ('52.5', '39.93333'), ('58.88333', '40.25'), ('58.86667', '57.58333'), ('51.28333', '37.55'), ('64.43333', '76.5'), ('43.355298', '46.099175'), ('48.05', '39.93333'), ('45.36028', '40.69444'), ('54.76667', '20.6'), ('54.28333', '85.93333'), ('54.58333', '22.2'), ('51.28556', '106.52917'), ('55.61667', '40.65'), ('54.21667', '55.03333'), ('42.11667', '48.2'), ('56.26667', '62.91667'), ('44.56667', '135.61667'), ('45.93333', '133.73333'), ('58.18333', '40.18333'), ('53.25', '39.15'), ('56.7', '60.1'), ('55.86667', '37.13333'), ('55.26667', '31.51667'), ('42.06917', '48.29583'), ('54.1530861', '33.2902917'), ('45.70861', '34.39333'), ('56.23333', '43.45'), ('55.63333', '37.85'), ('55.95', '92.38333'), ('43.15', '44.15'), ('54.23333', '49.58333'), ('52.12889', '35.07556'), ('56.34667', '37.52167'), ('52.505504', '35.141478'), ('57.83333', '29.96667'), ('58.45', '56.41667'), ('55.93333', '37.5'), ('47.31667', '142.8'), ('55.44389', '37.75806'), ('48.3369194', '39.9448917'), ('53.96667', '38.31667'), ('54.92', '33.30778'), ('55.74444', '38.84944'), ('56.75', '37.15'), ('49.05', '44.83333'), ('69.4', '86.18333'), ('55.2', '32.41667'), ('55.48333', '54.86667'), ('53.6', '34.33333'), ('45.2', '33.35833'), ('55.38333', '39.03361'), ('46.71056', '38.27778'), ('56.83333', '60.58333'), ('55.76667', '52.03333'), ('52.61667', '38.46667'), ('53.18333', '158.38333'), ('54.56667', '33.16667'), ('54.75', '61.31667'), ('62.58333', '50.85'), ('58.46667', '92.13333'), ('55.20556', '36.57'), ('51.35', '48.28333'), ('44.04306', '42.86417'), ('53.149167', '38.082585'), ('44.13333', '43.03333'), ('56.58333', '104.11667'), ('56.25', '93.53333'), ('52.339174', '35.351582'), ('51.83333', '41.46667'), ('53.4', '49.5'), ('53.75028', '34.73611'), ('50.98028', '44.78083'), ('55.03333', '36.75'), ('53.53333', '33.73333'), ('55.60111', '38.11611'), ('50.11667', '129.43333'), ('56.5', '66.55'), ('57.48333', '42.13333'), ('56.6425', '43.39278'), ('52.38333', '38.91667'), ('55.3', '52.01667'), ('50.38333', '103.28333'), ('55.96667', '94.7'), ('69.4', '32.45'), ('56.26667', '32.08333'), ('69.41667', '30.8'), ('54.76528', '38.88361'), ('53.2', '45.16667'), ('56.81667', '61.31667'), ('53.7', '84.91667'), ('55.96667', '48.01667'), ('55.73333', '36.85'), ('48.01667', '40.11667'), ('56.1', '94.58333'), ('54.95', '20.48333'), ('55.85', '48.51667'), ('44.4070115', '43.8731235'), ('46.846525', '40.3040333'), ('53.73333', '127.25'), ('53.91667', '102.05'), ('55.16667', '59.66667'), ('52.43333', '31.73333'), ('51.16667', '82.16667'), ('48.58333', '45.75'), ('56.16667', '34.58333'), ('58.403333', '51.130361'), ('59.375', '28.20528'), ('57', '41'), ('55.97', '37.92'), ('60.68333', '60.43333'), ('67.46667', '86.56667'), ('56.85306', '53.21222'), ('42.56667', '47.86667'), ('45.36667', '41.71667'), ('56.23333', '96.06667'), ('53.85', '46.35'), ('55.763633', '48.736553'), ('53.86667', '44.36667'), ('66.0398139', '60.1315194'), ('45.71667', '42.9'), ('57.66667', '63.06667'), ('52.28333', '104.3'), ('54.90889', '71.26056'), ('54.63333', '83.3'), ('55.91667', '36.86667'), ('56.11667', '69.5'), ('53.45444', '56.04389'), ('56.63278', '47.89583'), ('59.5', '40.33333'), ('55.79083', '49.11444'), ('48.68333', '43.53333'), ('50.42583', '41.01556'), ('55.05', '74.58333'), ('54.71667', '20.5'), ('51.5', '44.45'), ('53.51667', '87.26667'), ('54.53333', '36.26667'), ('57.23333', '37.85'), ('56.26667', '54.2'), ('53.18333', '44.05'), ('60.95081', '29.130882'), ('56.4', '61.93333'), ('48.31667', '40.26667'), ('53.79194', '81.34861'), ('56.34917', '40.99778'), ('46.11556', '48.07694'), ('50.08333', '45.4'), ('56.85', '62.71667'), ('55.50694', '47.49139'), ('67.15694', '32.41167'), ('56.2', '95.7'), ('56.30889', '38.70139'), ('55.48333', '60.2'), ('43.306285', '44.909763'), ('53.73333', '78.03333'), ('43.769713', '41.911369'), ('53.11667', '34.98333'), ('55.2', '80.28333'), ('61.5', '38.93333'), ('59.76667', '60'), ('53.05', '60.65'), ('54.95', '41.39722'), ('55.88333', '60.75'), ('42.88333', '47.63333'), ('54.75', '58.2'), ('56.3', '62.56667'), ('58.7', '59.48333'), ('57.35', '37.61667'), ('54.83333', '38.15'), ('57.56667', '79.56667'), ('55.35417', '86.08972'), ('64.95', '34.6'), ('45.33861', '36.46806'), ('59.05', '57.65'), ('43.2', '46.86667'), ('43.85', '46.71667'), ('53.96667', '38.53333'), ('56.86667', '37.35'), ('59.36667', '28.6'), ('53.23333', '50.61667'), ('57.45', '42.15'), ('53.93333', '37.93333'), ('57.78333', '108.1'), ('56.15', '38.86667'), ('59.86667', '38.38333'), ('59.45', '32.01667'), ('54.08333', '34.3'), ('58.6', '49.65'), ('57.43333', '60.06667'), ('58.55', '50.01667'), ('59.86667', '30.98333'), ('67.61417', '33.67167'), ('59.337167', '52.245472'), ('52.65', '42.73333'), ('53.98333', '86.7'), ('43.90333', '42.72444'), ('56.33389', '36.7125'), ('52.75278', '32.23611'), ('55.81667', '45.03333'), ('67.55944', '30.46667'), ('56.36056', '41.31972'), ('54.03333', '43.91667'), ('62.26667', '74.48333'), ('58.6', '99.18333'), ('54.03333', '35.78333'), ('55.83333', '48.25'), ('56.33333', '46.56667'), ('68.88306', '33.02194'), ('58.8252278', '44.311444'), ('55.09389', '38.76806'), ('58.31667', '82.91667'), ('56.3', '39.38333'), ('59.625', '30.4'), ('50.55', '137'), ('57.03333', '40.38333'), ('56.7', '36.76667'), ('62.2', '34.26667'), ('54.8', '35.93333'), ('47.58333', '41.1'), ('55.1', '61.61667'), ('53.91667', '40.01667'), ('45.46667', '39.45'), ('54.88333', '61.4'), ('55.91667', '37.81667'), ('50.81361', '37.18139'), ('46.63333', '142.76667'), ('61.3', '47.16667'), ('55.93333', '39.63333'), ('64.58333', '30.6'), ('57.76667', '40.93333'), ('55.6625', '37.86722'), ('47.63333', '43.13333'), ('58.3', '48.33333'), ('61.25', '46.65'), ('50.31667', '44.8'), ('52.58333', '41.5'), ('56.93333', '41.08333'), ('60.96667', '46.48333'), ('56.12278', '38.14611'), ('51.01667', '45.7'), ('60.4', '57.06667'), ('55.81667', '37.33333'), ('45.03333', '38.98333'), ('56.43806', '38.22944'), ('54.95', '22.5'), ('55.6', '37.03333'), ('50.1', '118.03333'), ('58.08333', '55.75'), ('45.955306', '33.795'), ('48.7', '44.56667'), ('54.43333', '43.78333'), ('59.76667', '60.2'), ('58.35', '60.05'), ('56.61667', '57.76667'), ('56.012083', '92.871295'), ('50.95', '46.96667'), ('47.88333', '40.06667'), ('58.06329', '37.122983'), ('54.88917', '37.12333'), ('45.43333', '40.56667'), ('44.93333', '38'), ('56.15167', '44.19556'), ('55.57639', '36.69472'), ('51.48333', '57.35'), ('57.03333', '34.16667'), ('59.90694', '30.50556'), ('59.01667', '54.66667'), ('53.11667', '46.6'), ('55.45028', '78.3075'), ('56.1825', '50.90639'), ('55.41667', '42.51667'), ('52.76667', '55.78333'), ('57.43333', '56.93333'), ('54.36667', '77.3'), ('55.44083', '65.34111'), ('44.88333', '40.6'), ('45.25', '147.883333'), ('55.45', '40.61667'), ('55.58333', '38.91667'), ('51.71667', '36.18333'), ('54.9', '64.43333'), ('43.20444', '46.087812'), ('51.66667', '35.65'), ('55.33333', '59.43333'), ('58.28333', '59.73333'), ('51.7', '94.36667'), ('55.7', '60.55'), ('50.35', '106.45'), ('44.63333', '40.73333'), ('66.65806', '66.38389'), ('45.3925', '47.355'), ('54.56667', '20.16667'), ('55.4', '49.55'), ('56.01694', '39.94944'), ('61.25', '75.16667'), ('61.51667', '30.2'), ('53.0115528', '39.1281167'), ('54.5988694', '52.4422722'), ('54.65', '86.16667'), ('48.7', '45.2'), ('60.71667', '114.9'), ('44.10528', '42.97167'), ('58.63333', '59.78333'), ('45.46667', '133.4'), ('58.23333', '92.48333'), ('52.425306', '37.608306'), ('55.71528', '38.95778'), ('52.61667', '39.6'), ('53.95', '37.7'), ('50.98222', '39.49944'), ('57.11667', '35.46667'), ('56.01194', '37.47444'), ('60.73333', '33.55'), ('55.86667', '38.2'), ('58.73333', '29.85'), ('60.61667', '47.28333'), ('55.03833', '44.49778'), ('54.96667', '39.025'), ('56.01278', '45.02528'), ('58.1003806', '57.8043278'), ('55.58361', '37.90556'), ('51.66667', '35.26667'), ('59.35', '31.25'), ('55.68139', '37.89389'), ('58.35', '40.7'), ('53.86667', '34.46667'), ('61.61667', '72.16667'), ('59.56667', '150.8'), ('43.16667', '44.81667'), ('53.38333', '59.03333'), ('44.611', '40.111'), ('43.630508', '44.067733'), ('48.61667', '142.78333'), ('57.88333', '43.8'), ('55.2', '67.25'), ('58.85', '32.21667'), ('43.508882', '44.585563'), ('56.52278', '50.68083'), ('52.4', '36.5'), ('55', '36.46667'), ('55.7', '51.4'), ('54.46667', '19.93333'), ('58.33333', '44.76667'), ('56.21667', '87.75'), ('56.11667', '47.71667'), ('51.7', '46.75'), ('42.98333', '47.5'), ('53.06111', '32.84833'), ('61.03306', '76.10972'), ('62.91667', '34.45'), ('51.422085', '57.595296'), ('54.96667', '35.86667'), ('54.24167', '57.96778'), ('53.68333', '88.05'), ('65.85', '44.23333'), ('55.33333', '41.63333'), ('52.95', '55.93333'), ('55.9', '52.31667'), ('55.71667', '53.08333'), ('54.31667', '35.28333'), ('55.05', '60.1'), ('62.35', '50.06667'), ('48.91667', '40.4'), ('44.20083', '43.1125'), ('53.7', '91.68333'), ('55.06667', '57.55'), ('62.76028', '40.33528'), ('62.53333', '113.95'), ('54.23333', '39.03333'), ('50.06667', '43.23333'), ('56.43333', '59.11667'), ('45.130012', '42.027487'), ('52.89222', '40.49278'), ('53.73333', '119.76667'), ('55.5', '36.03333'), ('56.45', '52.21667'), ('43.74722', '44.65694'), ('67.93944', '32.91556'), ('48.35', '41.83333'), ('53.45', '41.8'), ('54.48333', '34.98333'), ('55.75583', '37.61778'), ('63.79444', '74.49722'), ('59.38333', '48.96667'), ('60.04583', '30.44861'), ('68.96667', '33.08333'), ('55.5725', '42.05139'), ('53.27833', '36.575'), ('53.7', '87.81667'), ('55.91667', '37.73333'), ('57.78333', '38.45'), ('55.7', '52.33333'), ('55.53333', '42.2'), ('57.46667', '41.96667'), ('65.53333', '72.51667'), ('56.00639', '90.39139'), ('43.21667', '44.76667'), ('55.56667', '71.35'), ('43.485259', '43.607072'), ('46.68333', '47.85'), ('55.38333', '36.73333'), ('43.556734', '43.862222'), ('67.63778', '53.00667'), ('42.81667', '132.88333'), ('56.01667', '29.93333'), ('46.65', '141.86667'), ('44.63333', '41.93333'), ('57.48333', '60.2'), ('56.21667', '32.78333'), ('55.03333', '22.03333'), ('57.45', '40.58333'), ('51.98333', '116.58333'), ('56.65833', '124.725'), ('54.63333', '22.56667'), ('52.8', '51.16667'), ('56.08889', '54.24639'), ('44.75056', '44.97972'), ('61.1', '72.6'), ('58.29444', '43.87806'), ('60.93389', '76.58111'), ('55.63333', '51.81667'), ('54.9', '99.01667'), ('56.66667', '59.3'), ('53.53333', '43.68333'), ('56.32694', '44.0075'), ('57.91667', '59.96667'), ('58.08333', '60.71667'), ('58.62083', '59.84778'), ('53.15', '140.73333'), ('50.02722', '45.46306'), ('59.53333', '45.45'), ('53.71667', '46.08333'), ('59.7', '30.78333'), ('60.1', '32.3'), ('59.05', '60.6'), ('45.49333', '41.21694'), ('53.4', '83.93333'), ('50.51667', '42.66667'), ('51.31667', '39.21667'), ('64.41667', '40.81667'), ('52.53333', '31.93333'), ('45.1', '41.05'), ('53.73333', '87.08333'), ('53.1', '49.91667'), ('54.03333', '39.75'), ('54.03333', '38.26667'), ('43.96361', '43.63944'), ('57.03333', '29.33333'), ('44.71667', '37.76667'), ('55.01667', '82.91667'), ('52.96667', '37.05'), ('56.33333', '30.15'), ('51.20667', '58.32806'), ('50.45', '48.15'), ('54.15', '48.38333'), ('57.25', '60.08333'), ('51.1', '41.61667'), ('56.12194', '47.4925'), ('47.43583', '40.09861'), ('47.76667', '39.91667'), ('50.76667', '37.86667'), ('66.08472', '76.67889'), ('55.85', '38.43333'), ('57.55722', '49.93417'), ('69.33333', '88.21667'), ('63.20167', '75.45167'), ('54.43333', '50.8'), ('57.93333', '55.33333'), ('63.28333', '118.33333'), ('62.13333', '65.38333'), ('56.05', '59.6'), ('61.66667', '40.2'), ('49', '131.05'), ('55.1', '36.61667'), ('51.21111', '36.27639'), ('54.99167', '82.7125'), ('55.67333', '37.27333'), ('54.41667', '22.01667'), ('55.75', '60.71667'), ('54.857875', '38.5438194'), ('53.16667', '48.66667'), ('54.48333', '53.48333'), ('58.38333', '33.3'), ('68.15', '33.28333'), ('60.98333', '32.96667'), ('60.38333', '120.43333'), ('54.96667', '73.38333'), ('58.66667', '52.18333'), ('63.91667', '38.08333'), ('56.71667', '28.65'), ('51.76667', '55.1'), ('55.8', '38.96667'), ('58.53889', '48.89861'), ('51.2', '58.61667'), ('52.96667', '36.08333'), ('57.28333', '55.45'), ('53.61667', '87.33333'), ('57.15', '33.1'), ('57.33333', '28.35'), ('68.05306', '39.51306'), ('50.86667', '39.06667'), ('59.78333', '30.81667'), ('53.36667', '51.35'), ('53.58333', '142.93333'), ('57.71667', '55.38333'), ('57.88333', '54.71667'), ('55.96194', '43.09'), ('50.45', '40.06667'), ('55.78333', '38.65'), ('50.05', '46.88333'), ('43.13333', '133.13333'), ('69.7', '170.31667'), ('53.2', '45'), ('54.86667', '43.8'), ('56.91667', '59.95'), ('55.6', '44.55'), ('56.41667', '38.18333'), ('56.7381333', '38.8561528'), ('58.01389', '56.24889'), ('58.6', '35.81667'), ('50.13333', '45.21667'), ('51.28333', '108.83333'), ('52.31667', '45.38333'), ('61.79611', '34.34917'), ('53.01667', '158.65'), ('55.06667', '67.88333'), ('55.93333', '39.46667'), ('65.11667', '57.11667'), ('57.81667', '27.6'), ('59.51324', '34.17589'), ('54.95', '20.21667'), ('61.56667', '31.48333'), ('53.7', '37.3'), ('54.36667', '60.81667'), ('57.45', '41.5'), ('51.2', '42.25'), ('55.42972', '37.54444'), ('60.91667', '34.16667'), ('61.75', '75.58333'), ('55.91778', '39.175'), ('61.48333', '129.15'), ('56.45', '60.18333'), ('54.86667', '21.1'), ('54.6', '86.28333'), ('67.36583', '32.49806'), ('69.19833', '33.45611'), ('49.21667', '143.1'), ('57.76667', '29.55'), ('53.65', '52.13333'), ('52.93333', '33.45'), ('54.4', '32.45'), ('58.5', '39.11667'), ('54.45', '21.01667'), ('57.38333', '41.28333'), ('54.73333', '20'), ('60.36667', '28.61667'), ('46.05', '38.18333'), ('61.03333', '30.11667'), ('53.88333', '86.71667'), ('46.70306', '41.71917'), ('54.87944', '37.21389'), ('43.750055', '44.033333'), ('57.81667', '28.33333'), ('52.01667', '48.8'), ('61.8', '36.53333'), ('56.33333', '29.36667'), ('56.98333', '43.16667'), ('56.01667', '37.85'), ('54.83333', '37.61667'), ('57.06667', '27.91667'), ('60.75', '72.78333'), ('44.0499664', '43.0600548'), ('55.99778', '40.32972'), ('62.13333', '77.46667'), ('49.8', '129.4'), ('55.56667', '38.21667'), ('52.66667', '41.88333'), ('56.8', '59.91667'), ('57.36667', '61.4'), ('55.76667', '37.86667'), ('56.2655833', '34.3275694'), ('57.1', '41.73333'), ('53.94917', '32.85694'), ('50.2', '39.58333'), ('47.24056', '39.71056'), ('57.18333', '39.41667'), ('55.66361', '39.865'), ('52.25', '43.78333'), ('51.52722', '81.218806'), ('54.95', '31.06667'), ('55.6997667', '36.194417'), ('54.06667', '44.95'), ('58.05', '38.83333'), ('54.73333', '39.51667'), ('51.56667', '34.68333'), ('53.71667', '40.06667'), ('54.61667', '39.71667'), ('45.13361', '33.57722'), ('53.36667', '55.93333'), ('54.23333', '85.8'), ('66.53333', '66.63333'), ('46.48333', '41.53333'), ('53.18333', '50.11667'), ('59.95', '30.31667'), ('54.18333', '45.18333'), ('56.46667', '53.8'), ('51.53333', '46'), ('54.93333', '43.31667'), ('54.35', '41.91667'), ('55.05', '59.05'), ('55.1', '33.25'), ('53.1', '91.4'), ('54.11667', '102.16667'), ('54.93333', '20.15'), ('45.33083', '42.85111'), ('54.68333', '20.13333'), ('61.10833', '28.85833'), ('53.08333', '103.33333'), ('51.38333', '128.13333'), ('56.28333', '28.48333'), ('44.6', '33.53333'), ('50.68333', '156.11667'), ('55.63333', '109.31667'), ('64.56667', '39.85'), ('69.06917', '33.41667'), ('60.15', '59.93333'), ('56.6', '84.85'), ('52.15', '34.49389'), ('63.73333', '34.31667'), ('53.36944', '34.1'), ('47.51667', '40.8'), ('51.68333', '39.03333'), ('56.78944', '44.49056'), ('53.96667', '48.8'), ('49.58333', '42.73333'), ('55.53333', '45.46667'), ('56.3', '38.13333'), ('52.46667', '44.21667'), ('59.58333', '60.56667'), ('54.91667', '37.4'), ('60.15', '30.2'), ('52.7', '58.65'), ('54.98333', '57.68333'), ('44.94806', '34.10417'), ('53.98333', '123.93333'), ('53.81667', '39.55'), ('53', '78.65'), ('55.05', '21.66667'), ('45.25861', '38.12472'), ('59.11667', '28.08333'), ('58.724167', '50.161167'), ('51.66667', '103.7'), ('54.78278', '32.04528'), ('56.08333', '60.73333'), ('69.19417', '33.23306'), ('55.99', '40.01667'), ('55.08333', '21.88333'), ('57.601306', '48.938611'), ('53.93333', '37.63333'), ('48.9575', '140.2811111'), ('61.36667', '63.56667'), ('59.46667', '40.11667'), ('59.08333', '42.28333'), ('59.63333', '56.76667'), ('56.18444', '36.995'), ('51.16667', '54.98333'), ('61.33333', '46.91667'), ('58.11667', '30.31667'), ('52.43333', '53.15'), ('54', '90.25'), ('61.7', '30.66667'), ('54.05', '35.96667'), ('56.2543', '51.2812'), ('56.13333', '93.36667'), ('59.9', '29.08611'), ('63.58333', '53.93333'), ('43.58528', '39.72028'), ('54.41667', '34.03333'), ('55.13333', '40.16667'), ('44.6', '132.81667'), ('54.4', '40.38333'), ('53.93333', '43.18333'), ('67.458', '153.706'), ('56.98333', '60.46667'), ('52.25', '117.71667'), ('45.03333', '41.96667'), ('55.8', '38.18333'), ('57.98333', '31.35'), ('56.51667', '34.93333'), ('52.58333', '32.76667'), ('45.02917', '35.08861'), ('51.29806', '37.835'), ('53.63333', '55.95'), ('60.73333', '77.58333'), ('50.78333', '36.48333'), ('56.37333', '38.585'), ('54.88694', '38.07722'), ('54.11667', '36.5'), ('44.85139', '34.9725'), ('51.190694', '35.27083'), ('55.95', '40.86667'), ('56.42111', '40.44889'), ('43.313475', '45.051581'), ('62.08333', '32.36667'), ('53.01667', '32.4'), ('61.25', '73.43333'), ('48.6', '42.85'), ('53.08333', '45.7'), ('62.78333', '148.15'), ('54.1', '35.35'), ('56.90583', '62.03417'), ('53.16667', '48.46667'), ('61.66667', '50.81667'), ('56.5', '60.81667'), ('55.83333', '34.28333'), ('60.13333', '32.56667'), ('58.05', '65.26667'), ('47.23917', '38.88333'), ('56.06667', '85.61667'), ('55.93333', '98.01667'), ('56.73333', '37.53333'), ('57.0125', '63.72917'), ('52.71667', '41.43333'), ('56.902383', '74.37079'), ('64.91472', '77.77278'), ('54.71667', '37.18333'), ('55.21667', '75.96667'), ('52.76667', '87.86667'), ('56.8578278', '35.9219278'), ('43.449437', '41.74382'), ('56.85', '40.55'), ('54.63333', '43.21667'), ('45.26667', '37.38333'), ('43.48333', '44.13889'), ('54.93333', '48.83333'), ('45.61667', '38.93333'), ('59.63333', '33.5'), ('45.85', '40.11667'), ('58.19528', '68.25806'), ('55.23333', '84.38333'), ('53.51667', '49.41667'), ('47.76667', '142.06667'), ('58.96667', '126.26667'), ('56.48861', '84.95222'), ('55.28333', '85.61667'), ('57.03333', '34.96667'), ('56.5', '31.63333'), ('59.55', '30.9'), ('59.98333', '42.76667'), ('54.08333', '61.56667'), ('52.58333', '33.76667'), ('54.8', '58.45'), ('44.1', '39.08333'), ('54.6', '53.7'), ('54.2', '37.61667'), ('54.56667', '100.56667'), ('52.1446', '93.9181'), ('58.03333', '63.7'), ('57.88333', '39.53333'), ('55.15', '124.71667'), ('43.3892664', '42.9189065'), ('55.86667', '72.2'), ('57.15', '65.53333'), ('51.98333', '42.26667'), ('49.06667', '142.03333'), ('57.53333', '38.33333'), ('66.4', '112.3'), ('57.88333', '35.01667'), ('55.31667', '89.81667'), ('53.9791417', '38.1600833'), ('51.83333', '107.61667'), ('54.31667', '48.36667'), ('52.85', '32.68333'), ('60.13333', '64.78333'), ('57.46667', '45.78333'), ('57.11667', '50'), ('43.129123', '45.54167'), ('50.8', '42.01667'), ('65.995028', '57.557139'), ('52.05', '39.73333'), ('52.75', '103.65'), ('59.41667', '56.68333'), ('43.8', '131.95'), ('44.08611', '41.97194'), ('58', '102.66667'), ('54.93333', '58.16667'), ('56.8', '105.83333'), ('45.21528', '39.68944'), ('58.83333', '36.43333'), ('54.73333', '55.96667'), ('63.56667', '53.7'), ('54.31667', '59.38333'), ('55.81667', '94.31667'), ('52.08944', '35.85889'), ('45.04889', '35.37917'), ('53.45', '34.41667'), ('42.96667', '132.4'), ('49.76667', '43.65'), ('55.95', '38.05'), ('57.25', '41.1'), ('48.48333', '135.06667'), ('44.42389', '39.53722'), ('61', '69'), ('47.4', '47.25'), ('59.95', '40.2'), ('43.25', '46.58333'), ('52.48333', '48.1'), ('51.35', '110.45'), ('55.88917', '37.445'), ('57.15', '31.18333'), ('47.04028', '142.04306'), ('56.25', '37.98333'), ('55.86667', '47.48333'), ('47.64667', '42.09472'), ('51.7602528', '128.121175'), ('51.28333', '91.56667'), ('56.76667', '54.11667'), ('52.98333', '49.71667'), ('53.24167', '39.96667'), ('54.97778', '60.37'), ('56.11667', '47.23333'), ('43.566657', '43.583325'), ('54.1', '36.25'), ('55.16222', '61.40306'), ('60.4', '56.48333'), ('53.15', '103.06667'), ('54.21667', '83.36667'), ('59.11667', '37.9'), ('44.213888', '42.04431'), ('56.01472', '38.38972'), ('53.81667', '91.28333'), ('56.5', '56.08333'), ('54.63333', '21.81667'), ('55.145', '37.45556'), ('55.36667', '50.63333'), ('52.03333', '113.5'), ('56.76667', '43.25'), ('59.12806', '31.65917'), ('55.1', '80.96667'), ('58.28333', '57.81667'), ('58.75', '42.7'), ('58.78333', '56.15'), ('51.53333', '92.9'), ('56.08333', '63.63333'), ('43.145', '45.903847'), ('55.525', '89.2'), ('58.36667', '45.5'), ('55.5776722', '39.5446333'), ('47.7122111', '40.2083694'), ('57.67472', '46.62083'), ('54.03333', '41.7'), ('50.40778', '36.89694'), ('52.2', '104.1'), ('62.1', '42.9'), ('51.85', '116.03333'), ('52', '127.66667'), ('52.1137809', '47.199229'), ('59.941819', '31.034363'), ('55.5', '46.41667'), ('55.23333', '63.28333'), ('56.85', '41.36667'), ('51.88111', '36.90306'), ('55.21667', '62.76667'), ('54', '37.51667'), ('45.42361', '35.81861'), ('55.91667', '38'), ('55.88333', '38.78333'), ('55.8', '38.45'), ('55.71667', '38.21667'), ('46.31667', '44.26667'), ('51.46667', '46.11667'), ('51.83333', '40.8'), ('61.31667', '63.35'), ('56.58333', '42.01667'), ('46.95', '142.73333'), ('44.66667', '45.65'), ('54.45', '61.25'), ('55.73333', '84.9'), ('56.5', '39.68333'), ('57.31667', '43.1'), ('54.86667', '58.43333'), ('54.75', '35.23333'), ('55.95', '46.2'), ('62.02722', '129.73194'), ('44.49944', '34.15528'), ('56.65', '66.3'), ('56.26667', '54.93333'), ('57.303306', '47.868806'), ('52.93333', '78.58333'), ('57.61667', '39.85'), ('55.06667', '32.68333'), ('54.4793833', '37.6933556'), ('51.03333', '59.86667'), ('56.28333', '37.48333')]
    y, x = random.choice(a)
    y = float(y)
    x = float(x)
    y += random.randint(-100, 100) / 10000
    x += random.randint(-100, 100) / 10000
    return render_template('game.html', coords=f"{y}, {x}")


def main():
    db_session.global_init("db/panorama_db.sqlite")
    app.run()


main()

# Именно тут, а не вверху. Важен код выполняющийся внутри кода при импортировании
import scheduled.update_top as player_top

update_top_th = threading.Thread(target=player_top.schedule_update)
update_top_th.start()
