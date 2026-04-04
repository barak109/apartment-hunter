# 🏠 מצאן דירות — הוראות התקנה

## שלב 1 — צור Repository ב-GitHub

1. כנס ל-github.com ולחץ על **"New repository"** (הכפתור הירוק)
2. שם ה-repository: `apartment-hunter`
3. סמן **Public** (חשוב לדשבורד!)
4. לחץ **"Create repository"**

---

## שלב 2 — העלה את הקבצים

1. בדף שנפתח, לחץ על **"uploading an existing file"**
2. גרור את כל התיקיות והקבצים מהמחשב לשם:
   - תיקיית `scraper/`
   - תיקיית `dashboard/`
   - תיקיית `data/`
   - תיקיית `.github/`
3. לחץ **"Commit changes"**

---

## שלב 3 — הוסף את ה-Secrets (מפתחות)

1. ב-repository שלך לחץ על **Settings**
2. בצד שמאל לחץ על **Secrets and variables → Actions**
3. לחץ **"New repository secret"** והוסף:

   **GEMINI_API_KEY**
   הערך: המפתח שקיבלת מ-aistudio.google.com

   **FACEBOOK_GROUPS** (אופציונלי)
   הערך: קישורים לקבוצות מופרדים בפסיק, למשל:
   `https://www.facebook.com/groups/xxxxx,https://www.facebook.com/groups/yyyyy`

---

## שלב 4 — הפעל את GitHub Pages (הדשבורד)

1. ב-Settings של ה-repository
2. לחץ על **Pages** בצד שמאל
3. תחת Source בחר **Deploy from a branch**
4. Branch: **main** | Folder: **/dashboard**
5. לחץ **Save**

אחרי כמה דקות הדשבורד שלך יהיה זמין בכתובת:
`https://[שם-המשתמש-שלך].github.io/apartment-hunter`

---

## שלב 5 — הרץ את הסורק לראשונה

1. לחץ על **Actions** ב-repository
2. תראה את **"Apartment Hunter"**
3. לחץ עליו ואז **"Run workflow"** → **"Run workflow"**
4. המתן כ-2 דקות — הסורק ירוץ ויביא דירות!

---

## זהו! 🎉

מעכשיו הסורק ירוץ **אוטומטית כל 6 שעות** ויעדכן את הדשבורד.

---

## איך להוסיף קבוצות פייסבוק?

שלח לי את הקישורים לקבוצות הציבוריות שלך ואעדכן את הקוד.
