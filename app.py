from datetime import timedelta, datetime

import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests

API_URL = "https://app.kiphub.ru"
BOT_TOKEN = "7592076702:AAEnnuv69T-XYpKpeS6dCXXnoVfKsxqc4j4"
bot = telebot.TeleBot(BOT_TOKEN)

user_data = {}

last_interaction = {}
INACTIVITY_THRESHOLD = timedelta(minutes=30)

def check_inactivity_and_reset(message):
    """Проверка неактивности пользователя и вызов команды /start, если нужно."""
    current_time = datetime.now()
    user_id = message.chat.id

    # Проверяем, был ли пользователь неактивен более 30 минут
    if user_id in last_interaction:
        last_time = last_interaction[user_id]
        if current_time - last_time > INACTIVITY_THRESHOLD:
            # Если неактивен, вызываем /start
            start_handler(message)

    # Обновляем время последнего взаимодействия
    last_interaction[user_id] = current_time


def api_request(endpoint, method='GET', headers=None, data=None, params=None):
    """Универсальная функция для выполнения запросов к API."""
    url = f"{API_URL}/{endpoint}"
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers, params=params)
        elif method == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method == 'PUT':
            response = requests.put(url, headers=headers, json=data)
        elif method == 'DELETE':
            response = requests.delete(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"API error: {e}")
        return None

def process_email(message):
    """Обработка ввода email."""
    check_inactivity_and_reset(message)
    user_data[message.chat.id] = {"email": message.text}  # Сохраняем email
    bot.send_message(message.chat.id, "Введите ваш пароль:")
    bot.register_next_step_handler(message, process_password)

def process_password(message):
    """Обработка ввода пароля и авторизация."""
    check_inactivity_and_reset(message)
    user_data[message.chat.id]["password"] = message.text  # Сохраняем пароль

    email = user_data[message.chat.id]["email"]
    password = user_data[message.chat.id]["password"]
    role_id = 1  # Фиксированная роль для пользователя

    # Запрос к API
    response = api_request(
        'login',
        method='POST',
        data={"email": email, "password": password}
    )

    if response and response.get("role_id") == role_id:
        # Сохраняем данные пользователя
        user_data[message.chat.id].update(response)
        bot.send_message(message.chat.id, "Авторизация успешна!")

        # Проверяем, дал ли пользователь согласие
        if not user_data[message.chat.id].get("consent_given"):
            request_data_processing_consent(message)
        else:
            # Переход к следующему шагу
            contest_handler(message)
    else:
        bot.send_message(message.chat.id, "Ошибка авторизации. Проверьте ваши данные.")

def request_data_processing_consent(message):
    """Запрашиваем согласие на обработку персональных данных."""
    user_id = message.chat.id
    consent_text = (
        "Для продолжения использования бота, пожалуйста, подтвердите согласие на обработку персональных данных. "
        "Нажимая 'Принимаю', вы соглашаетесь с нашими условиями."
    )
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Принимаю", callback_data="consent_given"))
    bot.send_message(user_id, consent_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "consent_given")
def handle_consent_given(call):
    """Обработка согласия на обработку персональных данных."""
    user_id = call.message.chat.id
    user_data[user_id] = user_data.get(user_id, {})  # Убедимся, что данные пользователя существуют
    user_data[user_id]["consent_given"] = True  # Сохраняем согласие
    bot.send_message(user_id, "Спасибо за подтверждение! Теперь вы можете продолжить.")
    contest_handler(call.message)

def process_registration_last_name(message):
    check_inactivity_and_reset(message)
    user_data[message.chat.id]['last_name'] = message.text
    bot.send_message(message.chat.id, "Введите имя:")
    bot.register_next_step_handler(message, process_registration_first_name)

def process_registration_first_name(message):
    check_inactivity_and_reset(message)
    user_data[message.chat.id]['first_name'] = message.text
    bot.send_message(message.chat.id, "Введите email:")
    bot.register_next_step_handler(message, process_registration_email)

def process_registration_email(message):
    check_inactivity_and_reset(message)
    user_data[message.chat.id]['email'] = message.text
    bot.send_message(message.chat.id, "Введите номер телефона:")
    bot.register_next_step_handler(message, process_registration_phone)

def process_registration_phone(message):
    check_inactivity_and_reset(message)
    user_data[message.chat.id]['phone'] = message.text
    bot.send_message(message.chat.id, "Введите пароль:")
    bot.register_next_step_handler(message, process_registration_password)

def process_registration_password(message):
    check_inactivity_and_reset(message)
    user_data[message.chat.id]['password'] = message.text
    complete_registration(message)

def complete_registration(message):
    """Завершение регистрации через API и вывод кнопок."""
    check_inactivity_and_reset(message)
    data = {
        "last_name": user_data[message.chat.id]['last_name'],
        "first_name": user_data[message.chat.id]['first_name'],
        "email": user_data[message.chat.id]['email'],
        "phone": user_data[message.chat.id]['phone'],
        "password": user_data[message.chat.id]['password'],
        "role_id": 1
    }
    response = api_request('register', method='POST', data=data)

    if response:
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Заполнить анкету", callback_data="edit_profile"))
        markup.add(InlineKeyboardButton("Сделать это позже", callback_data="login_later"))
        bot.send_message(
            message.chat.id,
            "Регистрация завершена! Что хотите сделать дальше?",
            reply_markup=markup
        )
    else:
        bot.send_message(message.chat.id, "Ошибка регистрации. Попробуйте снова.")

@bot.callback_query_handler(func=lambda call: call.data in ["edit_profile", "login_later"])
def post_registration_handler(call):
    """Обработка действий после регистрации."""
    if call.data == "edit_profile":
        bot.send_message(call.message.chat.id, "Переход к заполнению анкеты...")
        edit_handler(call.message)  # Переход к /edit
    elif call.data == "login_later":
        bot.send_message(call.message.chat.id, "Вы можете авторизоваться. Используйте команду /login.")

def get_profile(message):
    """Получение данных профиля пользователя."""
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    if not user:
        bot.send_message(message.chat.id, "Сначала авторизуйтесь через /login")
        return

    # Запрос профиля через API
    response = api_request(f"universal/user?id_user={user['user_id']}")

    # Проверка структуры ответа
    if response:
        # Если response - это список, берем первый элемент
        if isinstance(response, list):
            profile = response[0]
        else:
            profile = response

        # Проверка, что профиль содержит нужные данные
        if isinstance(profile, dict):
            profile_text = (
                f"ID для конкурса: {user['user_id']}\n"
                f"Имя: {profile.get('first_name', 'Не указано')}\n"
                f"Фамилия: {profile.get('last_name', 'Не указано')}\n"
                f"Email: {profile.get('email', 'Не указано')}\n"
                f"Телефон: {profile.get('phone', 'Не указано')}\n"
            )
            bot.send_message(message.chat.id, f"Ваш профиль:\n{profile_text}")
        else:
            bot.send_message(message.chat.id, "Ошибка получения профиля: неожиданный формат данных.")
    else:
        bot.send_message(message.chat.id, "Ошибка получения профиля.")


def handle_education(call):
    """Редактирование раздела Образование."""
    user = user_data.get(call.message.chat.id)
    headers = {'Authorization': f'Bearer {user["token"]}'}
    markup = InlineKeyboardMarkup()
    # Получаем список образования
    response = api_request(f"api/educations/{user['user_id']}", headers=headers)
    if not response:
        markup.add(InlineKeyboardButton("Добавить", callback_data="add_education"))
        bot.send_message(call.message.chat.id, "Данные об образовании отсутствуют", reply_markup=markup)
        return

    # Формируем список с кнопками
    for edu in response:
        markup.add(InlineKeyboardButton(
            f"{edu['degree_name']} в {edu['university_name']} ({edu['start_date']} - {edu['end_date']})",
            callback_data=f"edu_{edu['id_education']}"
        ))
    markup.add(InlineKeyboardButton("Добавить", callback_data="add_education"))
    bot.send_message(call.message.chat.id, "Ваши записи об образовании:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "add_education")
def add_education_handler(call):
    """Добавление нового образования."""
    bot.send_message(call.message.chat.id, "В какой степени образования вы обучаетесь? (например, Бакалавриат, Магистратура)")
    bot.register_next_step_handler(call.message, process_education_degree)

def process_education_degree(message):
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    user['education'] = {'degree': message.text}

    # Сравниваем с доступными степенями
    response = api_request("api/degrees")
    degrees = list(set(d['name'] for d in response))
    if user['education']['degree'] not in degrees:
        bot.send_message(message.chat.id, f"Неверное значение. Попробуйте: {', '.join(degrees)}")
        bot.register_next_step_handler(message, process_education_degree)
        return

    bot.send_message(message.chat.id, "Введите название университета:")
    bot.register_next_step_handler(message, process_education_university)

def process_education_university(message):
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    user['education']['university'] = message.text

    # Проверяем университет
    response = api_request("api/universities")
    universities = list(set(u['name'] for u in response))
    if user['education']['university'] not in universities:
        bot.send_message(message.chat.id, f"Университет не найден. Попробуйте: {', '.join(universities)}")
        bot.register_next_step_handler(message, process_education_university)
        return

    bot.send_message(message.chat.id, "Введите направление (например, Радиоэлектроника, Программная инженерия):")
    bot.register_next_step_handler(message, process_education_direction)


def process_education_direction(message):
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    user['education']['direction'] = message.text

    # Проверяем направление
    response = api_request("api/directions")
    directions = list(set(d['name'] for d in response if d['name'] is not None))
    if user['education']['direction'] not in directions:
        bot.send_message(message.chat.id, f"Направление не найдено. Попробуйте: {', '.join(directions)}")
        bot.register_next_step_handler(message, process_education_direction)
        return

    bot.send_message(message.chat.id, "Введите группу (например, КИП-01):")
    bot.register_next_step_handler(message, process_education_group)

def process_education_group(message):
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    user['education']['group'] = message.text

    # Проверяем группу
    response = api_request("api/groups")
    groups = list(set(g['name'] for g in response))
    if user['education']['group'] not in groups:
        bot.send_message(message.chat.id, f"Группа не найдена. Попробуйте: {', '.join(groups)}")
        bot.register_next_step_handler(message, process_education_group)
        return

    bot.send_message(message.chat.id, "Введите год начала обучения (4 цифры):")
    bot.register_next_step_handler(message, process_education_start_year)

def process_education_start_year(message):
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)

    # Проверяем формат года
    if not message.text.isdigit() or len(message.text) != 4:
        bot.send_message(message.chat.id, "Введите корректный год в формате 'YYYY'.")
        bot.register_next_step_handler(message, process_education_start_year)
        return

    user['education']['start_year'] = message.text
    bot.send_message(message.chat.id, "Введите год окончания обучения (4 цифры):")
    bot.register_next_step_handler(message, process_education_end_year)

def process_education_end_year(message):
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)

    # Проверяем формат года
    if not message.text.isdigit() or len(message.text) != 4:
        bot.send_message(message.chat.id, "Введите корректный год в формате 'YYYY'.")
        bot.register_next_step_handler(message, process_education_end_year)
        return

    user['education']['end_year'] = message.text
    save_education(message)

def save_education(message):
    """Сохранение нового образования через API."""
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    headers = {'Authorization': f'Bearer {user["token"]}'}

    education_data = {
        "degree": user['education']['degree'],
        "university": user['education']['university'],
        "direction": user['education']['direction'],
        "group": user['education']['group'],
        "start_date": user['education']['start_year'] + "-01-01",
        "end_date": user['education']['end_year'] + "-01-01"
    }

    response = api_request(f"api/education/{user['user_id']}", method='POST', headers=headers, data=education_data)
    if response:
        bot.send_message(message.chat.id, "Образование успешно добавлено!")
    else:
        bot.send_message(message.chat.id, "Ошибка при сохранении данных об образовании.")


def handle_work_experience(call):
    """Редактирование раздела Опыт работы."""
    user = user_data.get(call.message.chat.id)
    headers = {'Authorization': f'Bearer {user["token"]}'}

    markup = InlineKeyboardMarkup()
    # Получаем список опыта
    response = api_request(f"api/works/{user['user_id']}", headers=headers)
    if not response:
        markup.add(InlineKeyboardButton("Добавить", callback_data="add_work"))
        bot.send_message(call.message.chat.id, "Отсутсвует опыт работы", reply_markup=markup)
        return

    # Формируем список с кнопками
    for work in response:
        markup.add(InlineKeyboardButton(
            f"{work['position']} в {', '.join(work['organizations'])} ({work['start_date']} - {work['end_date']})",
            callback_data=f"work_{work['id_work']}"
        ))
    markup.add(InlineKeyboardButton("Добавить", callback_data="add_work"))
    bot.send_message(call.message.chat.id, "Ваш опыт работы:", reply_markup=markup)

def handle_personal_data(call):
    """Редактирование личных данных пользователя."""
    user = user_data.get(call.message.chat.id)
    if not user:
        bot.send_message(call.message.chat.id, "Сначала авторизуйтесь через /login.")
        return

    # Получение текущих данных пользователя из API
    headers = {'Authorization': f'Bearer {user["token"]}'}
    response = api_request(f"universal/user?id_user={user['user_id']}", headers=headers)
    if not response:
        bot.send_message(call.message.chat.id, "Ошибка загрузки личных данных.")
        return

    # Отображаем текущие данные с возможностью редактирования
    profile = response[0]
    profile_text = (
        f"Ваши личные данные:\n"
        f"Имя: {profile['first_name']}\n"
        f"Фамилия: {profile['last_name']}\n"
        f"Email: {profile['email']}\n"
        f"Телефон: {profile['phone']}\n"
    )
    bot.send_message(call.message.chat.id, profile_text)

    # Кнопки для редактирования полей
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Изменить имя", callback_data="edit_first_name"))
    markup.add(InlineKeyboardButton("Изменить фамилию", callback_data="edit_last_name"))
    markup.add(InlineKeyboardButton("Изменить email", callback_data="edit_email"))
    markup.add(InlineKeyboardButton("Изменить телефон", callback_data="edit_phone"))
    bot.send_message(call.message.chat.id, "Что вы хотите изменить?", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: call.data == "edit_first_name")
def edit_first_name_handler(call):
    """Изменение имени пользователя."""
    bot.send_message(call.message.chat.id, "Введите новое имя:")
    bot.register_next_step_handler(call.message, update_first_name)


def update_first_name(message):
    """Обновление имени через API."""
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    headers = {'Authorization': f'Bearer {user["token"]}'}
    new_first_name = message.text

    response = api_request(
        f"universal/user?id_user={user['user_id']}",
        method='PUT',
        headers=headers,
        data={"first_name": new_first_name}
    )
    if response:
        bot.send_message(message.chat.id, "Имя успешно обновлено!")
    else:
        bot.send_message(message.chat.id, "Ошибка обновления имени.")


@bot.callback_query_handler(func=lambda call: call.data == "edit_last_name")
def edit_last_name_handler(call):
    """Изменение фамилии пользователя."""
    bot.send_message(call.message.chat.id, "Введите новую фамилию:")
    bot.register_next_step_handler(call.message, update_last_name)


def update_last_name(message):
    """Обновление фамилии через API."""
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    headers = {'Authorization': f'Bearer {user["token"]}'}
    new_last_name = message.text

    response = api_request(
        f"universal/user?id_user={user['user_id']}",
        method='PUT',
        headers=headers,
        data={"last_name": new_last_name}
    )
    if response:
        bot.send_message(message.chat.id, "Фамилия успешно обновлена!")
    else:
        bot.send_message(message.chat.id, "Ошибка обновления фамилии.")


@bot.callback_query_handler(func=lambda call: call.data == "edit_email")
def edit_email_handler(call):
    """Изменение email пользователя."""
    bot.send_message(call.message.chat.id, "Введите новый email:")
    bot.register_next_step_handler(call.message, update_email)


def update_email(message):
    """Обновление email через API."""
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    headers = {'Authorization': f'Bearer {user["token"]}'}
    new_email = message.text

    response = api_request(
        f"universal/user?id_user={user['user_id']}",
        method='PUT',
        headers=headers,
        data={"email": new_email}
    )
    if response:
        bot.send_message(message.chat.id, "Email успешно обновлен!")
    else:
        bot.send_message(message.chat.id, "Ошибка обновления email.")


@bot.callback_query_handler(func=lambda call: call.data == "edit_phone")
def edit_phone_handler(call):
    """Изменение телефона пользователя."""
    bot.send_message(call.message.chat.id, "Введите новый номер телефона:")
    bot.register_next_step_handler(call.message, update_phone)


def update_phone(message):
    """Обновление телефона через API."""
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    headers = {'Authorization': f'Bearer {user["token"]}'}
    new_phone = message.text

    response = api_request(
        f"universal/user?id_user={user['user_id']}",
        method='PUT',
        headers=headers,
        data={"phone": new_phone}
    )
    if response:
        bot.send_message(message.chat.id, "Телефон успешно обновлен!")
    else:
        bot.send_message(message.chat.id, "Ошибка обновления телефона.")


def handle_projects(call):
    """Редактирование раздела Проекты."""
    user = user_data.get(call.message.chat.id)
    headers = {'Authorization': f'Bearer {user["token"]}'}

    # Получаем список проектов
    markup = InlineKeyboardMarkup()
    response = api_request(f"api/projects/{user['user_id']}", headers=headers)
    if not response:
        markup.add(InlineKeyboardButton("Добавить", callback_data="add_project"))
        bot.send_message(call.message.chat.id, "Ошибка загрузки данных о проектах.", reply_markup=markup)
        return

    # Формируем список с кнопками
    for project in response:
        markup.add(InlineKeyboardButton(
            f"{project['project_name']} ({project['project_link']})",
            callback_data=f"project_{project['id_project']}"
        ))
    markup.add(InlineKeyboardButton("Добавить", callback_data="add_project"))
    bot.send_message(call.message.chat.id, "Ваши проекты:", reply_markup=markup)



@bot.message_handler(commands=['start'])
def start_handler(message):
    """Начальная команда /start."""
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Заполнить анкету участника📄", callback_data="generate_resume"))

    image_path = "contestMars.jpg"
    with open(image_path, 'rb') as photo:
        bot.send_photo(
            message.chat.id,
            photo,
            caption="""*Добро пожаловать на Карьерный Инженерный Портал\!* 🌟

🔧 *Для кого?*  
КИП создан для студентов, выпускников и профессионалов, которые стремятся построить успешную карьеру, а также для инновационных компаний, поддерживающих креативных инженеров\.

💼 *Что здесь можно делать?*

● Участвовать в конкурсах и зарабатывать баллы или денежные призы\. 
● Создавать профессиональные резюме за пару минут\.   
● Вступить в комьюнити технологических интузиастов\.   

🌐 *Присоединяйтесь к КИП уже сегодня\!*
        """,
            parse_mode='MarkdownV2',
            reply_markup=markup
        )

@bot.callback_query_handler(func=lambda call: call.data == "auth_student")
def auth_callback(call):
    """Команда /login."""
    bot.send_message(call.message.chat.id, "Введите ваш email:")
    bot.register_next_step_handler(call.message, process_email)


@bot.callback_query_handler(func=lambda call: call.data in ["edit_education", "edit_work", "edit_projects", "edit_personal"])
def edit_section_handler(call):
    """Обработчик выбора раздела для редактирования."""
    user = user_data.get(call.message.chat.id)
    if not user:
        bot.send_message(call.message.chat.id, "Сначала авторизуйтесь через /login.")
        return

    section = call.data
    if call.data == "edit_education":
        handle_education(call)
    elif call.data == "edit_work":
        handle_work_experience(call)
    elif call.data == "edit_projects":
        handle_projects(call)
    elif call.data == "edit_personal":
        handle_personal_data(call)

@bot.callback_query_handler(func=lambda call: True)
def start_callback_handler(call):
    """Обработчик кнопок из команды /start."""
    if call.data == "generate_resume":
        # Кнопки для авторизации или регистрации
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Авторизация", callback_data="auth_student"))
        markup.add(InlineKeyboardButton("Регистрация", callback_data="register_student"))
        bot.send_message(call.message.chat.id, "Вы уже были на портале?", reply_markup=markup)

    elif call.data == "find_engineer":
        # Кнопки для авторизации или регистрации с role_id=2
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("Авторизация", callback_data="auth_employer"))
        markup.add(InlineKeyboardButton("Регистрация", callback_data="register_employer"))
        bot.send_message(call.message.chat.id, "Выберите действие для авторизации в качестве роботодателя:", reply_markup=markup)



@bot.message_handler(commands=['login'])
def login_handler(message):
    """Команда /login."""
    check_inactivity_and_reset(message)
    bot.send_message(message.chat.id, "Введите ваш email:")
    bot.register_next_step_handler(message, process_email)

def process_email(message):
    """Обработка ввода email."""
    user_data[message.chat.id] = {"email": message.text}  # Сохраняем email
    bot.send_message(message.chat.id, "Введите ваш пароль:")
    bot.register_next_step_handler(message, process_password)

@bot.message_handler(commands=['registration'])
def registration_handler(message):
    """Команда /registration без разделения на роли."""
    check_inactivity_and_reset(message)
    # Устанавливаем роль пользователя по умолчанию
    user_data[message.chat.id] = {'role_id': 1}  # role_id = 1 для пользователя
    bot.send_message(message.chat.id, "Введите фамилию:")
    bot.register_next_step_handler(message, process_registration_last_name)


@bot.message_handler(commands=['profile'])
def profile_handler(message):
    """Команда /profile."""
    check_inactivity_and_reset(message)
    get_profile(message)
#

@bot.message_handler(commands=['resume'])
def resume_handler(message):
    """Команда /resume для генерации резюме."""
    user = user_data.get(message.chat.id)
    if not user:
        bot.send_message(message.chat.id, "Сначала авторизуйтесь через /login.")
        return

    user_id = user.get("user_id")
    id_pattern = 1  # ID шаблона по умолчанию
    token = user["token"]  # Токен аутентификации
    if not token:
        bot.send_message(message.chat.id, "Ошибка: токен не найден. Авторизуйтесь снова.")
        return

    # URL для генерации резюме
    url = f"https://app.kiphub.ru/pattern1/{user_id}"
    headers = {
        "Authorization": f"Bearer {token}",
        "accept": "application/json"  # Заголовок 'accept' обязателен
    }

    # Выполняем запрос
    response = requests.get(url, headers=headers, stream=True)

    if response.status_code == 200:
        bot.send_message(
            message.chat.id,
            f"Ваше резюме генерируется! Вы можете скачать его, перейдя по ссылке ниже:\n\n"
            f"[Скачать резюме (PDF)](https://app.kiphub.ru/login)",
            parse_mode="Markdown"
        )
    else:
        # Обрабатываем ошибку
        bot.send_message(
            message.chat.id,
            f"Ошибка при генерации резюме. Код: {response.status_code}, Ответ: {response.text}"
        )


@bot.message_handler(commands=['edit'])
def edit_handler(message):
    """Команда /edit для редактирования профиля."""
    check_inactivity_and_reset(message)
    user = user_data.get(message.chat.id)
    # bot.send_message(message.chat.id, "Функция изменения данных скоро будет доступна")
    if not user:
        bot.send_message(message.chat.id, "Сначала авторизуйтесь через /login.")
        return

    # Кнопки выбора раздела
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Образование", callback_data="edit_education"))
    markup.add(InlineKeyboardButton("Опыт работы", callback_data="edit_work"))
    markup.add(InlineKeyboardButton("Проекты", callback_data="edit_projects"))
    markup.add(InlineKeyboardButton("Личные данные", callback_data="edit_personal"))

    bot.send_message(
        message.chat.id,
        "Что вы хотите изменить?",
        reply_markup=markup
    )


@bot.message_handler(commands=['exit'])
def exit_handler(message):
    """Команда /exit."""
    check_inactivity_and_reset(message)
    if message.chat.id in user_data:
        del user_data[message.chat.id]
    bot.send_message(message.chat.id, "Вы успешно вышли.")

@bot.message_handler(commands=['contest'])
def contest_handler(message):
    """Команда /contest."""
    check_inactivity_and_reset(message)
    # Получаем данные пользователя из временного хранилища
    user = user_data.get(message.chat.id)
    if not user:
        bot.send_message(message.chat.id, "Сначала авторизуйтесь через /login")
        return

    # Получаем ID пользователя
    user_id = user.get('user_id')
    if not user_id:
        bot.send_message(message.chat.id, "Ошибка: не удалось получить ID пользователя. Попробуйте авторизоваться снова.")
        return

    image_path = "contest.jpg"

    # Отправляем фотографию с текстом
    with open(image_path, 'rb') as photo:
        bot.send_photo(
            message.chat.id,
            photo,
            caption=f"""*Колония на Марсе: псаномалия\!*

Запомните свой КИП ID: *{user_id}*
Ссылка для подачи ответа: https://forms\.gle/AsevmEgdYZekVsYE6 
    """,
            parse_mode='MarkdownV2'
        )
if __name__ == "__main__":
    bot.infinity_polling()