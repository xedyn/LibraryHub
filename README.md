# 📚 LibraryHub - System Zarządzania Biblioteką

## 📖 Opis projektu

LibraryHub to aplikacja webowa do zarządzania biblioteką, która umożliwia:

- **Wypożyczanie i zwracanie książek** z automatycznym systemem terminów
- **Zarządzanie katalogiem książek** z walidacją numerów ISBN
- **System kar za spóźnienia** z automatycznym naliczaniem
- **Panel administratora** z pełnymi uprawnieniami zarządzania
- **Automatyczne odliczanie czasu** wypożyczeń w czasie rzeczywistym

## 🛠️ Technologie

- **Backend:** Python Flask
- **Frontend:** HTML, CSS, JavaScript, Bootstrap 5
- **Baza danych:** SQLite
- **Bezpieczeństwo:** bcrypt (hashowanie haseł)
- **UI Framework:** Bootstrap 5.3.0
- **Ikony:** FontAwesome 6.0.0

## ⚡ Szybki start

### Wymagania
- Python 3.7+
- pip
- pip install Flask==2.3.2 Flask-Login==0.6.2 bcrypt==4.0.1 Werkzeug==2.3.7 itsdangerous==2.2.0 Jinja2==3.1.6 MarkupSafe==3.0.2 click==8.2.1 blinker==1.9.0 colorama==0.4.6

### Instalacja

```bash
# Sklonuj repozytorium
git clone https://github.com/xedyn/LibraryHub.git
cd LibraryHub
# Uruchom CMD w głównym folderze gdzie znajduje się app.py:

# Utwórz środowisko wirtualne
python -m venv venv

# Aktywuj środowisko
venv\Scripts\activate

# Następnie zainstaluj zależności
pip install Flask==2.3.2 Flask-Login==0.6.2 bcrypt==4.0.1 Werkzeug==2.3.7 itsdangerous==2.2.0 Jinja2==3.1.6 MarkupSafe==3.0.2 click==8.2.1 blinker==1.9.0 colorama==0.4.6

# Uruchom aplikację
python app.py
```

### Dostęp
Otwórz przeglądarkę i wejdź na: **http://localhost:5000**

### Domyślne konto admin
- **Login:** admin
- **Hasło:** admin123

## 🎯 Funkcjonalności

### 👤 Dla użytkowników:
- ✅ Rejestracja i logowanie
- ✅ Przeglądanie katalogu książek
- ✅ Wyszukiwanie po tytule, autorze, ISBN
- ✅ Wypożyczanie książek (limit: 3 książki)
- ✅ Zwracanie książek
- ✅ Profil z historią wypożyczeń
- ✅ Automatyczne odliczanie czasu zwrotu
- ✅ Podgląd kar za spóźnienia

### 🔧 Dla administratorów:
- ✅ Dodawanie książek z walidacją ISBN
- ✅ Edycja i usuwanie książek
- ✅ Zarządzanie użytkownikami
- ✅ Przeglądanie profili użytkowników
- ✅ Zarządzanie karami
- ✅ Oznaczanie książek jako zwrócone
- ✅ Statystyki najpopularniejszych książek

## 📊 Funkcje biznesowe

### System wypożyczeń:
- **Limit:** 3 książki na użytkownika
- **Okres:** 30 dni
- **Kary:** 0,60 PLN za dzień spóźnienia
- **ISBN:** Walidacja i unikalność numerów

### Bezpieczeństwo:
- Hashowanie haseł (bcrypt)
- Walidacja wszystkich danych wejściowych
- Kontrola uprawnień administratora
- Bezpieczne sesje użytkowników

## 📁 Struktura projektu

```
LibraryHub/
├── 📄 app.py                           # Główny plik aplikacji Flask
├── 📄 README.md                        # Dokumentacja projektu
├── 📂 database/                        # Folder bazy danych
│   ├── 📄 .gitkeep                     
│   └── 📄 library.db                   # Baza SQLite (auto-tworzona)
├── 📂 templates/                       # Szablony HTML
│   ├── 📄 base.html                    # Szablon bazowy z navbar
│   ├── 📄 index.html                   # Strona główna
│   ├── 📄 login.html                   # Formularz logowania
│   ├── 📄 register.html                # Formularz rejestracji
│   ├── 📄 catalog.html                 # Katalog książek
│   ├── 📄 profile.html                 # Profil użytkownika
│   ├── 📄 add_book.html                # Dodawanie książki (admin)
│   ├── 📄 edit_book.html               # Edycja książki (admin)
│   ├── 📄 manage_users.html            # Zarządzanie użytkownikami (admin)
│   ├── 📄 edit_user.html               # Edycja użytkownika (admin)
│   ├── 📄 manage_fines.html            # Zarządzanie karami (admin)
│   └── 📄 popular.html                 # Popularne książki
└── 📂 static/                          # Pliki statyczne
    └── 📄 logo.png                     # Logo aplikacji
```

# 🗄️ Struktura bazy danych

## 📊 Schemat relacyjny

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│    users    │    │    books    │    │   borrows   │    │    fines    │
├─────────────┤    ├─────────────┤    ├─────────────┤    ├─────────────┤
│ id (PK)     │    │ id (PK)     │    │ id (PK)     │    │ id (PK)     │
│ username    │    │ title       │    │ user_id (FK)│    │ user_id (FK)│
│ email       │    │ author      │    │ book_id (FK)│    │ amount      │
│ password    │    │ isbn        │    │ borrow_date │    │ reason      │
│ is_admin    │    │ available   │    │ due_date    │    │ paid        │
│ created_at  │    │ created_at  │    │ return_date │    │ created_at  │
└─────────────┘    └─────────────┘    │ returned    │    └─────────────┘
                                      └─────────────┘
```

## 🔒 Bezpieczeństwo danych

### Hashowanie haseł:
```python
# Używanie bcrypt z salt rounds = 12
password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
```

## 👥 Autor

**Krzysztof Rot**

## 📄 Licencja

Projekt został stworzony na potrzeby zaliczenia przedmiotu.

---

*LibraryHub - System Zarządzania Biblioteką 📚*
