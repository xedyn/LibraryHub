📚 LibraryHub - System Zarządzania Biblioteką

📖 Opis projektu
LibraryHub to aplikacja webowa do zarządzania biblioteką, która umożliwia:
* Wypożyczanie i zwracanie książek
* Zarządzanie katalogiem książek z numerami ISBN
* System kar za spóźnienia
* Panel administratora
* Automatyczne odliczanie czasu wypożyczeń

🛠️ Technologie
Backend: Python Flask
Frontend: HTML, CSS, JavaScript, Bootstrap 5
Baza danych: SQLite
Bezpieczeństwo: bcrypt (hashowanie haseł)
UI Framework: Bootstrap 5.3.0
Ikony: FontAwesome 6.0.0

⚡ Szybki start
Wymagania
Python 3.7+
pip

Instalacja
bash# Sklonuj repozytorium
git clone https://github.com/xedyn/LibraryHub.git
cd LibraryHub

# Zainstaluj zależności
pip install flask flask-login bcrypt

# Uruchom aplikację
python app.py
Dostęp
Otwórz przeglądarkę i wejdź na: http://localhost:5000

Domyślne konto admin
Login: admin
Hasło: admin123

🎯 Funkcjonalności
👤 Dla użytkowników:
✅ Rejestracja i logowanie
✅ Przeglądanie katalogu książek
✅ Wyszukiwanie po tytule, autorze, ISBN
✅ Wypożyczanie książek (limit: 3 książki)
✅ Zwracanie książek
✅ Profil z historią wypożyczeń
✅ Automatyczne odliczanie czasu zwrotu
✅ Podgląd kar za spóźnienia

🔧 Dla administratorów:
✅ Dodawanie książek z ISBN
✅ Edycja i usuwanie książek
✅ Zarządzanie użytkownikami
✅ Przeglądanie profili użytkowników
✅ Zarządzanie karami
✅ Oznaczanie książek jako zwrócone
✅ Statystyki najpopularniejszych książek

📊 Funkcje biznesowe
System wypożyczeń:
Limit: 3 książki na użytkownika
Okres: 30 dni
Kary: 0,60 PLN za dzień spóźnienia
ISBN: Walidacja i unikalność numerów

Bezpieczeństwo:
Hashowanie haseł (bcrypt)
Walidacja wszystkich danych wejściowych
Kontrola uprawnień administratora
Sesje użytkowników

📱 Interfejs
Responsywny design - działa na komputerze i telefonie
Kolorystyka dopasowana do logo - żółty, czerwony, niebieski, zielony
Automatyczny timer - odliczanie czasu w czasie rzeczywistym (aktualizowane co minute)
Intuicyjna nawigacja - przejrzyste menu i przyciski

🗄️ Struktura bazy danych
users - użytkownicy i administratorzy
books - katalog książek z ISBN
borrows - wypożyczenia z terminami
fines - kary za spóźnienia

LibraryHub/
├── 📄 app.py                           # Główny plik aplikacji Flask
├── 📄 README.md                        # Dokumentacja GitHub
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
└──  📂 static/                          # Pliki statyczne
    └── 📄 logo.png                     # Logo aplikacji

👥 Zespół
One man army -> Krzysztof Rot

📄 Licencja
Projekt został stworzony na potrzeby zaliczenia przedmiotu.

LibraryHub - Nowoczesne zarządzanie biblioteką! 📚✨
