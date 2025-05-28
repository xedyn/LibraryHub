from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import sqlite3
import bcrypt
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.secret_key = 'secret-key'  # Zmień na bezpieczniejszy
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Stałe konfiguracyjne
MAX_BORROWS_PER_USER = 3  # Maksymalna liczba wypożyczeń na użytkownika

# Klasa użytkownika
class User(UserMixin):
    def __init__(self, id, username, is_admin=False):
        self.id = str(id)
        self.username = username
        self.is_admin = bool(is_admin)

    def get_id(self):
        return str(self.id)

# Funkcje walidacji
def validate_username(username):
    """Walidacja nazwy użytkownika"""
    if not username or len(username.strip()) < 3:
        return False, "Nazwa użytkownika musi mieć co najmniej 3 znaki"
    if len(username) > 50:
        return False, "Nazwa użytkownika nie może być dłuższa niż 50 znaków"
    if not re.match("^[a-zA-Z0-9_]+$", username):
        return False, "Nazwa użytkownika może zawierać tylko litery, cyfry i podkreślenia"
    return True, ""

def validate_password(password):
    """Walidacja hasła"""
    if not password or len(password) < 6:
        return False, "Hasło musi mieć co najmniej 6 znaków"
    if len(password) > 100:
        return False, "Hasło nie może być dłuższe niż 100 znaków"
    return True, ""

def validate_book_data(title, author, available, isbn=None):
    """Walidacja danych książki"""
    if not title or len(title.strip()) < 1:
        return False, "Tytuł nie może być pusty"
    if len(title) > 200:
        return False, "Tytuł nie może być dłuższy niż 200 znaków"

    if not author or len(author.strip()) < 1:
        return False, "Autor nie może być pusty"
    if len(author) > 100:
        return False, "Autor nie może być dłuższy niż 100 znaków"

    # Walidacja ISBN
    if isbn:
        isbn_clean = isbn.replace('-', '').replace(' ', '')
        if not isbn_clean.isdigit() or len(isbn_clean) not in [10, 13]:
            return False, "ISBN musi mieć 10 lub 13 cyfr"
        if len(isbn_clean) == 13 and not isbn_clean.startswith('978'):
            return False, "13-cyfrowy ISBN musi zaczynać się od 978"

    try:
        available_int = int(available)
        if available_int < 0:
            return False, "Liczba dostępnych egzemplarzy nie może być ujemna"
        if available_int > 1000:
            return False, "Liczba dostępnych egzemplarzy nie może przekraczać 1000"
    except (ValueError, TypeError):
        return False, "Liczba dostępnych egzemplarzy musi być liczbą"

    return True, ""

def get_user_unpaid_fines_total(user_id):
    """Pobiera sumę nieopłaconych kar użytkownika"""
    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()
        c.execute('SELECT SUM(amount) FROM fines WHERE user_id = ? AND paid = 0', (user_id,))
        total = c.fetchone()[0]
        conn.close()
        return total if total else 0
    except Exception:
        return 0

def get_user_borrow_count(user_id):
    """Pobiera liczbę aktywnych wypożyczeń użytkownika"""
    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM borrows WHERE user_id = ? AND returned = 0', (user_id,))
        count = c.fetchone()[0]
        conn.close()
        return count
    except Exception:
        return 0

# Obliczanie dni spóźnienia i opłaty - POPRAWIONE
def calculate_fine(borrow_date, return_date, returned, actual_return_date=None):
    """Oblicza karę za spóźnienie"""
    try:
        return_date_obj = datetime.strptime(return_date, '%Y-%m-%d %H:%M:%S')

        if returned and actual_return_date:
            end_date = datetime.strptime(actual_return_date, '%Y-%m-%d %H:%M:%S')
        else:
            end_date = datetime.now()

        if end_date > return_date_obj:
            days_late = (end_date - return_date_obj).days
            fine = days_late * 0.60  # 0,60 PLN za dzień
            return max(fine, 0)
    except (ValueError, TypeError):
        return 0
    return 0

# Obliczanie pozostałego czasu zwrotu
def calculate_days_left(return_date):
    """Oblicza pozostałe dni do zwrotu"""
    try:
        return_date_obj = datetime.strptime(return_date, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        delta = return_date_obj - now
        days_left = delta.days + (1 if delta.seconds > 0 else 0)
        return max(days_left, 0)
    except (ValueError, TypeError):
        return 0

# Inicjalizacja bazy danych
def init_db():
    conn = sqlite3.connect('database/library.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY, username TEXT UNIQUE, password TEXT, is_admin INTEGER)''')
    c.execute('''CREATE TABLE IF NOT EXISTS books
                 (id INTEGER PRIMARY KEY, title TEXT, author TEXT, added_date TEXT,
                  available INTEGER, last_edited TEXT, isbn TEXT UNIQUE)''')
    c.execute('''CREATE TABLE IF NOT EXISTS borrows
                 (id INTEGER PRIMARY KEY, user_id INTEGER, book_id INTEGER,
                  borrow_date TEXT, return_date TEXT, returned INTEGER, fine_amount REAL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS fines
                 (id INTEGER PRIMARY KEY, borrow_id INTEGER, user_id INTEGER,
                  amount REAL, calculated_date TEXT, paid INTEGER)''')

    # Sprawdź czy kolumna ISBN istnieje, jeśli nie - dodaj
    c.execute("PRAGMA table_info(books)")
    columns = [column[1] for column in c.fetchall()]
    if 'isbn' not in columns:
        c.execute('ALTER TABLE books ADD COLUMN isbn TEXT')

    # Domyślny admin
    c.execute('SELECT COUNT(*) FROM users')
    if c.fetchone()[0] == 0:
        hashed = bcrypt.hashpw('admin123'.encode('utf-8'), bcrypt.gensalt())
        c.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                  ('admin', hashed.decode('utf-8'), 1))

    # Przykładowe książki z ISBN
    c.execute('SELECT COUNT(*) FROM books')
    if c.fetchone()[0] == 0:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        books = [
            ('Wiedźmin', 'Andrzej Sapkowski', 5, '978-83-7469-707-3'),
            ('Lalka', 'Bolesław Prus', 3, '978-83-240-0123-4'),
            ('Solaris', 'Stanisław Lem', 2, '978-83-7392-845-6'),
            ('Pan Tadeusz', 'Adam Mickiewicz', 4, '978-83-240-0567-8'),
            ('Quo Vadis', 'Henryk Sienkiewicz', 3, '978-83-240-0890-1')
        ]
        for title, author, available, isbn in books:
            c.execute('INSERT INTO books (title, author, added_date, available, last_edited, isbn) VALUES (?, ?, ?, ?, ?, ?)',
                      (title, author, now, available, now, isbn))

    conn.commit()
    conn.close()

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()
        c.execute('SELECT id, username, is_admin FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()
        if user:
            return User(user[0], user[1], user[2])
    except Exception:
        pass
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/catalog')
def catalog():
    search = request.args.get('search', '').strip()
    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()
        if search:
            c.execute('''SELECT * FROM books
                        WHERE title LIKE ? OR author LIKE ? OR isbn LIKE ?
                        ORDER BY title''',
                      ('%' + search + '%', '%' + search + '%', '%' + search + '%'))
        else:
            c.execute('SELECT * FROM books ORDER BY title')
        books = c.fetchall()

        # Sprawdzenie wypożyczonych książek i limitu
        borrowed_books = []
        user_borrow_count = 0
        if current_user.is_authenticated:
            c.execute('SELECT book_id FROM borrows WHERE user_id = ? AND returned = 0', (current_user.id,))
            borrowed_books = [row[0] for row in c.fetchall()]
            user_borrow_count = len(borrowed_books)

        conn.close()
        return render_template('catalog.html',
                               books=books,
                               borrowed_books=borrowed_books,
                               user_borrow_count=user_borrow_count,
                               max_borrows=MAX_BORROWS_PER_USER)
    except Exception as e:
        return render_template('catalog.html',
                               books=[],
                               borrowed_books=[],
                               user_borrow_count=0,
                               max_borrows=MAX_BORROWS_PER_USER,
                               error=f"Błąd: {str(e)}")

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Walidacja
        valid, error = validate_username(username)
        if not valid:
            return render_template('login.html', error=error)

        if not password:
            return render_template('login.html', error='Hasło nie może być puste')

        try:
            conn = sqlite3.connect('database/library.db')
            c = conn.cursor()
            c.execute('SELECT id, username, password, is_admin FROM users WHERE username = ?', (username,))
            user = c.fetchone()
            conn.close()

            if user and bcrypt.checkpw(password.encode('utf-8'), user[2].encode('utf-8')):
                login_user(User(user[0], user[1], user[3]))
                return redirect(url_for('index'))
            else:
                return render_template('login.html', error='Błędny login lub hasło')
        except Exception as e:
            return render_template('login.html', error='Błąd logowania')

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        # Walidacja
        valid, error = validate_username(username)
        if not valid:
            return render_template('register.html', error=error)

        valid, error = validate_password(password)
        if not valid:
            return render_template('register.html', error=error)

        try:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
            conn = sqlite3.connect('database/library.db')
            c = conn.cursor()
            c.execute('INSERT INTO users (username, password, is_admin) VALUES (?, ?, ?)',
                      (username, hashed.decode('utf-8'), 0))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return render_template('register.html', error='Nazwa użytkownika już istnieje')
        except Exception as e:
            return render_template('register.html', error='Błąd rejestracji')

    return render_template('register.html')

@app.route('/add_book', methods=['GET', 'POST'])
@login_required
def add_book():
    if not current_user.is_admin:
        return redirect(url_for('catalog'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        author = request.form.get('author', '').strip()
        available = request.form.get('available', '')
        isbn = request.form.get('isbn', '').strip()

        # Walidacja
        valid, error = validate_book_data(title, author, available, isbn)
        if not valid:
            return render_template('add_book.html', error=error)

        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            conn = sqlite3.connect('database/library.db')
            c = conn.cursor()

            # Sprawdź czy ISBN już istnieje
            if isbn:
                isbn_clean = isbn.replace('-', '').replace(' ', '')
                c.execute('SELECT id FROM books WHERE isbn = ?', (isbn_clean,))
                if c.fetchone():
                    conn.close()
                    return render_template('add_book.html', error='Książka z tym ISBN już istnieje')

            c.execute('INSERT INTO books (title, author, added_date, available, last_edited, isbn) VALUES (?, ?, ?, ?, ?, ?)',
                      (title, author, now, int(available), now, isbn_clean if isbn else None))
            conn.commit()
            conn.close()
            return redirect(url_for('catalog'))
        except sqlite3.IntegrityError:
            return render_template('add_book.html', error='Książka z tym ISBN już istnieje')
        except Exception as e:
            return render_template('add_book.html', error=f"Błąd: {str(e)}")

    return render_template('add_book.html')

@app.route('/edit_book/<int:book_id>', methods=['GET', 'POST'])
@login_required
def edit_book(book_id):
    if not current_user.is_admin:
        return redirect(url_for('catalog'))

    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()

        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            author = request.form.get('author', '').strip()
            available = request.form.get('available', '')
            isbn = request.form.get('isbn', '').strip()

            # Walidacja
            valid, error = validate_book_data(title, author, available, isbn)
            if not valid:
                c.execute('SELECT * FROM books WHERE id = ?', (book_id,))
                book = c.fetchone()
                conn.close()
                return render_template('edit_book.html', book=book, error=error)

            try:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                isbn_clean = isbn.replace('-', '').replace(' ', '') if isbn else None

                # Sprawdź czy ISBN już istnieje (ale nie dla tej samej książki)
                if isbn_clean:
                    c.execute('SELECT id FROM books WHERE isbn = ? AND id != ?', (isbn_clean, book_id))
                    if c.fetchone():
                        c.execute('SELECT * FROM books WHERE id = ?', (book_id,))
                        book = c.fetchone()
                        conn.close()
                        return render_template('edit_book.html', book=book, error='Książka z tym ISBN już istnieje')

                c.execute('UPDATE books SET title = ?, author = ?, available = ?, last_edited = ?, isbn = ? WHERE id = ?',
                          (title, author, int(available), now, isbn_clean, book_id))
                conn.commit()
                conn.close()
                return redirect(url_for('catalog'))
            except sqlite3.IntegrityError:
                c.execute('SELECT * FROM books WHERE id = ?', (book_id,))
                book = c.fetchone()
                conn.close()
                return render_template('edit_book.html', book=book, error='Książka z tym ISBN już istnieje')

        c.execute('SELECT * FROM books WHERE id = ?', (book_id,))
        book = c.fetchone()
        conn.close()

        if not book:
            return redirect(url_for('catalog'))
        return render_template('edit_book.html', book=book)

    except Exception as e:
        return redirect(url_for('catalog'))

@app.route('/delete_book/<int:book_id>')
@login_required
def delete_book(book_id):
    if not current_user.is_admin:
        return redirect(url_for('catalog'))

    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()

        # Sprawdź czy książka nie jest wypożyczona
        c.execute('SELECT COUNT(*) FROM borrows WHERE book_id = ? AND returned = 0', (book_id,))
        if c.fetchone()[0] > 0:
            conn.close()
            # Przekieruj z błędem
            return redirect(url_for('catalog'))

        c.execute('DELETE FROM books WHERE id = ?', (book_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

    return redirect(url_for('catalog'))

@app.route('/borrow_book/<int:book_id>')
@login_required
def borrow_book(book_id):
    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()

        # Sprawdź limit wypożyczeń
        user_borrow_count = get_user_borrow_count(current_user.id)
        if user_borrow_count >= MAX_BORROWS_PER_USER:
            conn.close()
            return redirect(url_for('catalog'))

        # Sprawdzenie dostępności
        c.execute('SELECT available FROM books WHERE id = ?', (book_id,))
        book = c.fetchone()

        # Sprawdzenie czy już wypożyczona
        c.execute('SELECT id FROM borrows WHERE user_id = ? AND book_id = ? AND returned = 0',
                  (current_user.id, book_id))
        already_borrowed = c.fetchone()

        if book and book[0] > 0 and not already_borrowed:
            now = datetime.now()
            return_date = (now + timedelta(days=30)).strftime('%Y-%m-%d %H:%M:%S')

            c.execute('UPDATE books SET available = ? WHERE id = ?', (book[0] - 1, book_id))
            c.execute('INSERT INTO borrows (user_id, book_id, borrow_date, return_date, returned, fine_amount) VALUES (?, ?, ?, ?, ?, ?)',
                      (current_user.id, book_id, now.strftime('%Y-%m-%d %H:%M:%S'), return_date, 0, 0))
            conn.commit()

        conn.close()
    except Exception:
        pass

    return redirect(url_for('catalog'))

@app.route('/return_book/<int:book_id>')
@login_required
def return_book(book_id):
    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()

        # Pobranie informacji o wypożyczeniu
        c.execute('SELECT id, return_date FROM borrows WHERE user_id = ? AND book_id = ? AND returned = 0',
                  (current_user.id, book_id))
        borrow = c.fetchone()

        if borrow:
            now = datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')

            # Obliczenie kary
            fine = calculate_fine(now_str, borrow[1], True, now_str)

            # Aktualizacja książki
            c.execute('SELECT available FROM books WHERE id = ?', (book_id,))
            book = c.fetchone()
            if book:
                c.execute('UPDATE books SET available = ? WHERE id = ?', (book[0] + 1, book_id))

            # Aktualizacja wypożyczenia
            c.execute('UPDATE borrows SET returned = ?, return_date = ?, fine_amount = ? WHERE id = ?',
                      (1, now_str, fine, borrow[0]))

            # Dodanie kary jeśli istnieje
            if fine > 0:
                c.execute('INSERT INTO fines (borrow_id, user_id, amount, calculated_date, paid) VALUES (?, ?, ?, ?, ?)',
                          (borrow[0], current_user.id, fine, now_str, 0))

            conn.commit()

        conn.close()
    except Exception:
        pass

    return redirect(url_for('catalog'))

@app.route('/popular')
def popular():
    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()
        c.execute('''
            SELECT b.id, b.title, b.author, COUNT(br.id) as borrow_count
            FROM books b
            LEFT JOIN borrows br ON b.id = br.book_id
            GROUP BY b.id
            ORDER BY borrow_count DESC
            LIMIT 20
        ''')
        books = c.fetchall()
        conn.close()
        return render_template('popular.html', books=books)
    except Exception:
        return render_template('popular.html', books=[])

@app.route('/manage_users')
@login_required
def manage_users():
    if not current_user.is_admin:
        return redirect(url_for('catalog'))

    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()
        # Pobierz użytkowników wraz z liczbą aktywnych wypożyczeń
        c.execute('''
            SELECT u.id, u.username, u.is_admin,
                   COALESCE(COUNT(b.id), 0) as active_borrows
            FROM users u
            LEFT JOIN borrows b ON u.id = b.user_id AND b.returned = 0
            GROUP BY u.id, u.username, u.is_admin
            ORDER BY u.username
        ''')
        users = c.fetchall()
        conn.close()
        return render_template('manage_users.html', users=users)
    except Exception:
        return render_template('manage_users.html', users=[])

@app.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if not current_user.is_admin:
        return redirect(url_for('catalog'))

    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()

        if request.method == 'POST':
            username = request.form.get('username', '').strip()
            is_admin = 1 if request.form.get('is_admin') == 'on' else 0
            password = request.form.get('password', '').strip()

            # Walidacja
            valid, error = validate_username(username)
            if not valid:
                c.execute('SELECT id, username, is_admin FROM users WHERE id = ?', (user_id,))
                user = c.fetchone()
                conn.close()
                return render_template('edit_user.html', user=user, error=error)

            if password:
                valid, error = validate_password(password)
                if not valid:
                    c.execute('SELECT id, username, is_admin FROM users WHERE id = ?', (user_id,))
                    user = c.fetchone()
                    conn.close()
                    return render_template('edit_user.html', user=user, error=error)

            try:
                if password:
                    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
                    c.execute('UPDATE users SET username = ?, password = ?, is_admin = ? WHERE id = ?',
                              (username, hashed.decode('utf-8'), is_admin, user_id))
                else:
                    c.execute('UPDATE users SET username = ?, is_admin = ? WHERE id = ?',
                              (username, is_admin, user_id))
                conn.commit()
                conn.close()
                return redirect(url_for('manage_users'))
            except sqlite3.IntegrityError:
                c.execute('SELECT id, username, is_admin FROM users WHERE id = ?', (user_id,))
                user = c.fetchone()
                conn.close()
                return render_template('edit_user.html', user=user, error='Nazwa użytkownika już istnieje')

        c.execute('SELECT id, username, is_admin FROM users WHERE id = ?', (user_id,))
        user = c.fetchone()
        conn.close()

        if not user:
            return redirect(url_for('manage_users'))
        return render_template('edit_user.html', user=user)

    except Exception:
        return redirect(url_for('manage_users'))

@app.route('/delete_user/<int:user_id>')
@login_required
def delete_user(user_id):
    if not current_user.is_admin or user_id == int(current_user.id):
        return redirect(url_for('manage_users'))

    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()

        # Sprawdź czy użytkownik ma aktywne wypożyczenia
        c.execute('SELECT COUNT(*) FROM borrows WHERE user_id = ? AND returned = 0', (user_id,))
        if c.fetchone()[0] > 0:
            conn.close()
            return redirect(url_for('manage_users'))

        c.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
    except Exception:
        pass

    return redirect(url_for('manage_users'))

@app.route('/manage_fines')
@login_required
def manage_fines():
    if not current_user.is_admin:
        return redirect(url_for('catalog'))

    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()
        c.execute('''
            SELECT f.id, u.username, b.title, f.amount, f.calculated_date, f.paid, br.id, br.borrow_date
            FROM fines f
            JOIN users u ON f.user_id = u.id
            JOIN borrows br ON f.borrow_id = br.id
            JOIN books b ON br.book_id = b.id
            WHERE f.paid = 0
            ORDER BY f.calculated_date DESC
        ''')
        fines = c.fetchall()
        conn.close()
        return render_template('manage_fines.html', fines=fines)
    except Exception:
        return render_template('manage_fines.html', fines=[])

@app.route('/pay_fine/<int:borrow_id>')
@login_required
def pay_fine(borrow_id):
    if not current_user.is_admin:
        return redirect(url_for('catalog'))

    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()

        # Oznacz karę jako zapłaconą
        c.execute('UPDATE fines SET paid = 1 WHERE borrow_id = ?', (borrow_id,))

        # Sprawdź czy wypożyczenie już nie zostało zwrócone
        c.execute('SELECT returned FROM borrows WHERE id = ?', (borrow_id,))
        borrow = c.fetchone()

        if borrow and not borrow[0]:
            # Zwróć książkę jeśli jeszcze nie została zwrócona
            c.execute('SELECT book_id FROM borrows WHERE id = ?', (borrow_id,))
            book_id = c.fetchone()[0]

            c.execute('SELECT available FROM books WHERE id = ?', (book_id,))
            available = c.fetchone()[0]

            c.execute('UPDATE books SET available = ? WHERE id = ?', (available + 1, book_id))
            c.execute('UPDATE borrows SET returned = 1, return_date = ? WHERE id = ?',
                      (datetime.now().strftime('%Y-%m-%d %H:%M:%S'), borrow_id))

        conn.commit()
        conn.close()
    except Exception:
        pass

    return redirect(url_for('manage_fines'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        new_password = request.form.get('password', '')

        # Walidacja
        valid, error = validate_password(new_password)
        if not valid:
            borrows_with_days = get_user_borrows()
            user_borrow_count = get_user_borrow_count(current_user.id)
            unpaid_fines_total = get_user_unpaid_fines_total(current_user.id)
            return render_template('profile.html', error=error, borrows=borrows_with_days,
                                   message=None, viewed_user=None, user_borrow_count=user_borrow_count,
                                   max_borrows=MAX_BORROWS_PER_USER, unpaid_fines_total=unpaid_fines_total)

        try:
            hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
            conn = sqlite3.connect('database/library.db')
            c = conn.cursor()
            c.execute('UPDATE users SET password = ? WHERE id = ?', (hashed.decode('utf-8'), current_user.id))
            conn.commit()
            conn.close()

            # Pobierz dane do wyświetlenia
            borrows_with_days = get_user_borrows()
            user_borrow_count = get_user_borrow_count(current_user.id)
            unpaid_fines_total = get_user_unpaid_fines_total(current_user.id)
            return render_template('profile.html', message='Hasło zmienione pomyślnie',
                                   borrows=borrows_with_days, error=None, viewed_user=None,
                                   user_borrow_count=user_borrow_count, max_borrows=MAX_BORROWS_PER_USER,
                                   unpaid_fines_total=unpaid_fines_total)
        except Exception:
            borrows_with_days = get_user_borrows()
            user_borrow_count = get_user_borrow_count(current_user.id)
            unpaid_fines_total = get_user_unpaid_fines_total(current_user.id)
            return render_template('profile.html', error="Błąd zmiany hasła",
                                   borrows=borrows_with_days, message=None, viewed_user=None,
                                   user_borrow_count=user_borrow_count, max_borrows=MAX_BORROWS_PER_USER,
                                   unpaid_fines_total=unpaid_fines_total)

    # GET request
    borrows_with_days = get_user_borrows()
    user_borrow_count = get_user_borrow_count(current_user.id)
    unpaid_fines_total = get_user_unpaid_fines_total(current_user.id)
    return render_template('profile.html', borrows=borrows_with_days, message=None,
                           error=None, viewed_user=None, user_borrow_count=user_borrow_count,
                           max_borrows=MAX_BORROWS_PER_USER, unpaid_fines_total=unpaid_fines_total)

def get_user_borrows():
    """Pomocnicza funkcja do pobierania wypożyczeń użytkownika"""
    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()
        c.execute('''
            SELECT b.title, br.borrow_date, br.return_date, br.returned, br.fine_amount
            FROM borrows br
            JOIN books b ON br.book_id = b.id
            WHERE br.user_id = ?
            ORDER BY br.borrow_date DESC
        ''', (current_user.id,))
        borrows = c.fetchall()
        conn.close()

        # Oblicz dni pozostałe
        borrows_with_days = []
        for borrow in borrows:
            days_left = calculate_days_left(borrow[2]) if not borrow[3] else None
            fine = borrow[4] if borrow[4] else 0
            borrows_with_days.append((borrow[0], borrow[1], borrow[2], borrow[3], days_left, fine))

        return borrows_with_days
    except Exception:
        return []

@app.route('/view_user_profile/<int:user_id>')
@login_required
def view_user_profile(user_id):
    """Widok profilu użytkownika dla administratora"""
    if not current_user.is_admin:
        return redirect(url_for('catalog'))

    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()

        # Pobierz dane użytkownika
        c.execute('SELECT id, username, is_admin FROM users WHERE id = ?', (user_id,))
        user_data = c.fetchone()

        if not user_data:
            conn.close()
            return redirect(url_for('manage_users'))

        viewed_user = User(user_data[0], user_data[1], user_data[2])

        # Pobierz wypożyczenia użytkownika
        c.execute('''
            SELECT b.title, br.borrow_date, br.return_date, br.returned, br.fine_amount
            FROM borrows br
            JOIN books b ON br.book_id = b.id
            WHERE br.user_id = ?
            ORDER BY br.borrow_date DESC
        ''', (user_id,))
        borrows = c.fetchall()
        conn.close()

        # Oblicz dni pozostałe
        borrows_with_days = []
        for borrow in borrows:
            days_left = calculate_days_left(borrow[2]) if not borrow[3] else None
            fine = borrow[4] if borrow[4] else 0
            borrows_with_days.append((borrow[0], borrow[1], borrow[2], borrow[3], days_left, fine))

        return render_template('profile.html',
                               borrows=borrows_with_days,
                               viewed_user=viewed_user,
                               message=None,
                               error=None,
                               user_borrow_count=len([b for b in borrows_with_days if not b[3]]),
                               max_borrows=MAX_BORROWS_PER_USER,
                               unpaid_fines_total=get_user_unpaid_fines_total(user_id))

    except Exception:
        return redirect(url_for('manage_users'))

@app.route('/admin_return_book/<int:user_id>/<book_title>')
@login_required
def admin_return_book(user_id, book_title):
    """Funkcja dla admina do oznaczania książki jako zwróconej"""
    if not current_user.is_admin:
        return redirect(url_for('catalog'))

    try:
        conn = sqlite3.connect('database/library.db')
        c = conn.cursor()

        # Znajdź aktywne wypożyczenie
        c.execute('''
            SELECT br.id, br.return_date, br.book_id
            FROM borrows br
            JOIN books b ON br.book_id = b.id
            WHERE br.user_id = ? AND b.title = ? AND br.returned = 0
        ''', (user_id, book_title))

        borrow = c.fetchone()

        if borrow:
            now = datetime.now()
            now_str = now.strftime('%Y-%m-%d %H:%M:%S')

            # Oblicz karę
            fine = calculate_fine(now_str, borrow[1], True, now_str)

            # Aktualizuj dostępność książki
            c.execute('SELECT available FROM books WHERE id = ?', (borrow[2],))
            book = c.fetchone()
            if book:
                c.execute('UPDATE books SET available = ? WHERE id = ?', (book[0] + 1, borrow[2]))

            # Oznacz jako zwróconą
            c.execute('UPDATE borrows SET returned = ?, return_date = ?, fine_amount = ? WHERE id = ?',
                      (1, now_str, fine, borrow[0]))

            # Dodaj karę jeśli istnieje
            if fine > 0:
                c.execute('INSERT INTO fines (borrow_id, user_id, amount, calculated_date, paid) VALUES (?, ?, ?, ?, ?)',
                          (borrow[0], user_id, fine, now_str, 0))

            conn.commit()

        conn.close()

    except Exception:
        pass

    return redirect(url_for('view_user_profile', user_id=user_id))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == '__main__':
    init_db()
    app.run(debug=True)