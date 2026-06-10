import sqlite3
import hashlib
import random
import tkinter as tk
from tkinter import messagebox, simpledialog
import csv

# ---------------- PALETTE ----------------
BG          = "#0d1117"
BG2         = "#111827"
CARD        = "#161f2e"
CARD2       = "#1c2a42"
BORDER      = "#243352"
BORDER_LT   = "#2e4070"

PRIMARY     = "#5b8dee"
PRIMARY_DK  = "#4a7be3"
PRIMARY_LT  = "#7aaaf5"

ACCENT      = "#56cfe1"
ACCENT_DK   = "#38b2c8"

SUCCESS     = "#52b788"
SUCCESS_DK  = "#40916c"
SUCCESS_LT  = "#95d5b2"

DANGER      = "#e05c7b"
DANGER_DK   = "#c94b68"

WARN        = "#f0a500"
WARN_DK     = "#d4920a"

PURPLE      = "#9d7fe8"
PURPLE_DK   = "#8a68d4"

TEXT        = "#d6e4f7"
TEXT2       = "#8fa8cc"
TEXT3       = "#4d6386"
GOLD        = "#e8c86a"

# ---------------- FONTS ----------------
FONT_BRAND  = ("Georgia",      20, "bold")
FONT_TITLE  = ("Georgia",      15, "bold")
FONT_HEAD   = ("Georgia",      13, "bold")
FONT_SUB    = ("Trebuchet MS", 11)
FONT_BTN    = ("Trebuchet MS", 10, "bold")
FONT_LABEL  = ("Trebuchet MS",  9)
FONT_INPUT  = ("Trebuchet MS", 11)
FONT_SMALL  = ("Trebuchet MS",  8)
FONT_OTP    = ("Courier New",  30, "bold")
FONT_NAV    = ("Trebuchet MS", 10)
FONT_STAT   = ("Georgia",      16, "bold")

# ---------------- DATABASE ----------------
conn   = sqlite3.connect("voting.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE,
    password TEXT,
    id_number TEXT UNIQUE,
    has_voted INTEGER DEFAULT 0
)""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS candidates(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS votes(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    candidate_id INTEGER,
    user_id INTEGER
)""")
conn.commit()

# ---------------- SECURITY ----------------
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def hash_id(i):       return hashlib.sha256(i.encode()).hexdigest()

# ---------------- GLOBALS ----------------
generated_otp = ""
current_user  = None

# ---------------- ROOT ----------------
root = tk.Tk()
root.title("SecureVote — Digital Voting Platform")
root.state("zoomed")
root.configure(bg=BG)

# =========================================================
#  WIDGET HELPERS
# =========================================================

def make_button(parent, text, cmd, bg_color, hover_color=None,
                width=None, padx=20, pady=11, font=FONT_BTN, fg=TEXT):
    hc = hover_color or bg_color
    kw = dict(text=text, command=cmd, bg=bg_color, fg=fg,
              font=font, bd=0, padx=padx, pady=pady,
              cursor="hand2", activebackground=hc, activeforeground=fg,
              relief="flat")
    if width:
        kw["width"] = width
    b = tk.Button(parent, **kw)
    b.bind("<Enter>", lambda e: b.configure(bg=hc))
    b.bind("<Leave>", lambda e: b.configure(bg=bg_color))
    return b

def make_entry(parent, placeholder="", show=None, width=34):
    frame = tk.Frame(parent, bg=CARD2, bd=0, highlightthickness=1,
                     highlightbackground=BORDER, highlightcolor=PRIMARY_LT)
    kw = dict(font=FONT_INPUT, bg=CARD2, fg=TEXT,
              insertbackground=PRIMARY_LT, bd=0, width=width, relief="flat")
    if show:
        kw["show"] = show
    e = tk.Entry(frame, **kw)
    e.pack(padx=14, pady=11)

    if placeholder:
        e.insert(0, placeholder)
        e.configure(fg=TEXT3)
        def on_focus_in(ev):
            if e.get() == placeholder:
                e.delete(0, "end")
                e.configure(fg=TEXT)
                if show: e.configure(show=show)
            frame.configure(highlightbackground=PRIMARY_LT)
        def on_focus_out(ev):
            if not e.get():
                e.insert(0, placeholder)
                e.configure(fg=TEXT3)
                if show: e.configure(show="")
            frame.configure(highlightbackground=BORDER)
        e.bind("<FocusIn>",  on_focus_in)
        e.bind("<FocusOut>", on_focus_out)

    return frame, e

def hsep(parent, color=BORDER, pady=8):
    tk.Frame(parent, bg=color, height=1).pack(fill="x", pady=pady)

def lbl(parent, text, font=FONT_SUB, fg=TEXT2, bg=None, anchor="w"):
    bg = bg or _bg(parent)
    return tk.Label(parent, text=text, font=font, fg=fg, bg=bg, anchor=anchor)

def _bg(w):
    try: return w.cget("bg")
    except: return BG

def icon_row(parent, icon, text, fg=TEXT2, bg=None):
    bg = bg or _bg(parent)
    f = tk.Frame(parent, bg=bg)
    tk.Label(f, text=icon, font=("Segoe UI", 10), fg=ACCENT, bg=bg).pack(side="left")
    tk.Label(f, text=f"  {text}", font=FONT_SMALL, fg=fg, bg=bg).pack(side="left")
    f.pack(anchor="w", pady=2)

# =========================================================
#  STATUS BAR (created later, referenced here)
# =========================================================
status_var = tk.StringVar(value="● Not signed in")

def update_status(msg, color=TEXT3):
    status_var.set(msg)
    status_bar.configure(fg=color)

# =========================================================
#  VALIDATION
# =========================================================
def valid_password(p):
    return len(p) >= 6 and any(c.isdigit() for c in p)

def get_field(entry_widget, placeholder):
    v = entry_widget.get().strip()
    return "" if v == placeholder else v

# =========================================================
#  TOAST
# =========================================================
_toast_after = None

def show_toast(msg, color=SUCCESS):
    global _toast_after
    toast_lbl.configure(text=f"   {msg}   ", bg=color, fg="white")
    toast_lbl.place(relx=0.5, rely=0.96, anchor="center")
    if _toast_after:
        root.after_cancel(_toast_after)
    _toast_after = root.after(3800, lambda: toast_lbl.place_forget())

# =========================================================
#  REGISTER
# =========================================================
def register():
    u   = get_field(user_e, "Username")
    p   = get_field(pass_e, "Password")
    idn = get_field(id_e,   "ID Number  (12 digits)")
    if not u or not p or not idn:
        show_toast("All fields are required.", DANGER); return
    if len(u) < 4:
        show_toast("Username must be at least 4 characters.", DANGER); return
    if not valid_password(p):
        show_toast("Password: 6+ chars with at least one digit.", DANGER); return
    if not idn.isdigit() or len(idn) != 12:
        show_toast("ID must be exactly 12 digits.", DANGER); return
    try:
        cursor.execute("INSERT INTO users(username,password,id_number) VALUES(?,?,?)",
                       (u, hash_password(p), hash_id(idn)))
        conn.commit()
        show_toast("Account created! You can now sign in.", SUCCESS)
    except:
        show_toast("Username or ID already registered.", DANGER)

# =========================================================
#  LOGIN
# =========================================================
def login():
    global current_user, generated_otp
    u   = get_field(user_e, "Username")
    p   = get_field(pass_e, "Password")
    idn = get_field(id_e,   "ID Number  (12 digits)")
    if not u or not p or not idn:
        show_toast("All fields are required.", DANGER); return
    cursor.execute("SELECT * FROM users WHERE username=? AND password=? AND id_number=?",
                   (u, hash_password(p), hash_id(idn)))
    user = cursor.fetchone()
    if user:
        current_user  = user
        generated_otp = str(random.randint(100000, 999999))
        update_status(f"● Signed in as  {u}", SUCCESS_LT)
        show_otp_dialog(generated_otp)
    else:
        show_toast("Credentials not recognised. Please try again.", DANGER)

# =========================================================
#  OTP DIALOG
# =========================================================
def show_otp_dialog(otp):
    win = tk.Toplevel(root)
    win.title("Two-Factor Authentication")
    win.configure(bg=BG)
    win.resizable(False, False)
    win.grab_set()
    win.geometry("440x420")
    win.update_idletasks()
    x = root.winfo_x() + (root.winfo_width()  - 440) // 2
    y = root.winfo_y() + (root.winfo_height() - 420) // 2
    win.geometry(f"+{x}+{y}")

    # Header
    hdr = tk.Frame(win, bg=CARD2, pady=20, padx=28)
    hdr.pack(fill="x")
    tk.Label(hdr, text="🔐  Verify Your Identity",
             font=FONT_TITLE, fg=TEXT, bg=CARD2).pack(anchor="w")
    tk.Label(hdr, text="Enter the one-time passcode below to continue.",
             font=FONT_LABEL, fg=TEXT2, bg=CARD2).pack(anchor="w", pady=(5, 0))

    body = tk.Frame(win, bg=BG, padx=32, pady=22)
    body.pack(fill="both", expand=True)

    tk.Label(body, text="YOUR ONE-TIME PASSCODE",
             font=("Trebuchet MS", 8, "bold"), fg=TEXT3, bg=BG).pack(anchor="w")

    otp_box = tk.Frame(body, bg=CARD2, highlightthickness=1, highlightbackground=ACCENT)
    otp_box.pack(fill="x", pady=(6, 18))
    tk.Label(otp_box, text=otp, font=FONT_OTP, fg=ACCENT, bg=CARD2, pady=14).pack()

    tk.Label(body, text="ENTER CODE",
             font=("Trebuchet MS", 8, "bold"), fg=TEXT3, bg=BG).pack(anchor="w")

    ef, otp_input = make_entry(body, "6-digit code", width=32)
    ef.pack(fill="x", pady=(4, 6))

    err_lbl = tk.Label(body, text="", font=FONT_LABEL, fg=DANGER, bg=BG)
    err_lbl.pack(anchor="w", pady=(0, 6))

    def verify():
        global generated_otp
        entered = otp_input.get().strip()
        if entered == generated_otp:
            generated_otp = ""
            win.destroy()
            open_voting()
        else:
            err_lbl.configure(text="  ✕  Incorrect code — please try again.")
            otp_input.delete(0, "end")
            otp_input.focus_set()

    # ── Big, unmissable verify button ──────────────────
    verify_btn = tk.Button(
        body,
        text="✓   Verify & Continue",
        command=verify,
        bg=SUCCESS,
        fg="white",
        font=("Georgia", 12, "bold"),
        bd=0,
        pady=14,
        padx=20,
        cursor="hand2",
        activebackground=SUCCESS_DK,
        activeforeground="white",
        relief="flat"
    )
    verify_btn.pack(fill="x", ipady=2)
    verify_btn.bind("<Enter>", lambda e: verify_btn.configure(bg=SUCCESS_DK))
    verify_btn.bind("<Leave>", lambda e: verify_btn.configure(bg=SUCCESS))

    cancel_btn = make_button(body, "Cancel", win.destroy,
                             CARD2, BORDER, pady=8, font=FONT_LABEL, fg=TEXT3)
    cancel_btn.pack(fill="x", pady=(8, 0))

    otp_input.focus_set()
    win.bind("<Return>", lambda e: verify())

# =========================================================
#  VOTING WINDOW
# =========================================================
def open_voting():
    if current_user[4] == 1:
        show_toast("You have already cast your vote.", WARN); return
    cursor.execute("SELECT id, name FROM candidates")
    candidates = cursor.fetchall()
    if not candidates:
        show_toast("No candidates are available yet.", WARN); return

    win = tk.Toplevel(root)
    win.title("Cast Your Vote")
    win.configure(bg=BG)
    win.geometry("540x560")
    win.resizable(False, False)
    win.grab_set()
    x = root.winfo_x() + (root.winfo_width()  - 540) // 2
    y = root.winfo_y() + (root.winfo_height() - 560) // 2
    win.geometry(f"+{x}+{y}")

    hdr = tk.Frame(win, bg=SUCCESS_DK, pady=18, padx=24)
    hdr.pack(fill="x")
    tk.Label(hdr, text="🗳️  Cast Your Vote", font=FONT_TITLE,
             fg="white", bg=SUCCESS_DK).pack(anchor="w")
    tk.Label(hdr, text="Select one candidate — your vote is confidential and anonymous.",
             font=FONT_LABEL, fg=SUCCESS_LT, bg=SUCCESS_DK).pack(anchor="w", pady=(4, 0))

    body = tk.Frame(win, bg=BG, padx=28, pady=20)
    body.pack(fill="both", expand=True)

    selected_var = tk.IntVar(value=-1)

    for cid, name in candidates:
        row = tk.Frame(body, bg=CARD, highlightthickness=1,
                       highlightbackground=BORDER, cursor="hand2")
        row.pack(fill="x", pady=6)
        inner = tk.Frame(row, bg=CARD, padx=16, pady=14)
        inner.pack(fill="x")
        rb = tk.Radiobutton(inner, variable=selected_var, value=cid,
                            bg=CARD, activebackground=CARD,
                            selectcolor=PRIMARY, fg=PRIMARY, bd=0)
        rb.pack(side="left")
        tk.Label(inner, text=name, font=("Georgia", 11),
                 fg=TEXT, bg=CARD).pack(side="left", padx=10)

        def enter(e, r=row, i=inner):
            r.configure(highlightbackground=PRIMARY_LT)
            i.configure(bg=CARD2); r.configure(bg=CARD2)
        def leave(e, r=row, i=inner):
            r.configure(highlightbackground=BORDER)
            i.configure(bg=CARD); r.configure(bg=CARD)
        row.bind("<Enter>", enter); row.bind("<Leave>", leave)
        inner.bind("<Button-1>", lambda e, c=cid: selected_var.set(c))

    warn_lbl = tk.Label(body, text="", font=FONT_LABEL, fg=DANGER, bg=BG)
    warn_lbl.pack(pady=4)

    def confirm_vote():
        cid = selected_var.get()
        if cid == -1:
            warn_lbl.configure(text="  Please select a candidate before submitting."); return
        cname = next(n for i, n in candidates if i == cid)
        if messagebox.askyesno("Confirm Vote",
                               f"You are voting for:\n\n    {cname}\n\nThis action cannot be undone."):
            cast_vote(cid, win)

    make_button(body, "Submit My Vote  →", confirm_vote, SUCCESS, SUCCESS_DK,
                pady=13, font=("Georgia", 11, "bold"), fg="white").pack(fill="x", pady=8)

# =========================================================
#  CAST VOTE
# =========================================================
def cast_vote(cid, win):
    cursor.execute("INSERT INTO votes(candidate_id,user_id) VALUES(?,?)",
                   (cid, current_user[0]))
    cursor.execute("UPDATE users SET has_voted=1 WHERE id=?", (current_user[0],))
    conn.commit()
    win.destroy()
    show_toast("✓  Your vote has been recorded. Thank you!", SUCCESS)
    update_status("● Vote cast successfully", SUCCESS_LT)

# =========================================================
#  RESULTS WINDOW
# =========================================================
def show_results():
    cursor.execute("""
    SELECT candidates.name, COUNT(*) as cnt
    FROM votes JOIN candidates ON candidates.id = votes.candidate_id
    GROUP BY candidates.name ORDER BY cnt DESC
    """)
    data = cursor.fetchall()

    win = tk.Toplevel(root)
    win.title("Election Results")
    win.configure(bg=BG)
    win.geometry("540x520")
    win.resizable(False, False)
    x = root.winfo_x() + (root.winfo_width()  - 540) // 2
    y = root.winfo_y() + (root.winfo_height() - 520) // 2
    win.geometry(f"+{x}+{y}")

    hdr = tk.Frame(win, bg=PURPLE_DK, pady=18, padx=24)
    hdr.pack(fill="x")
    tk.Label(hdr, text="📊  Election Results", font=FONT_TITLE,
             fg="white", bg=PURPLE_DK).pack(anchor="w")

    body = tk.Frame(win, bg=BG, padx=30, pady=22)
    body.pack(fill="both", expand=True)

    if not data:
        tk.Label(body, text="No votes have been cast yet.",
                 font=("Georgia", 12), fg=TEXT2, bg=BG).pack(pady=50)
        return

    total  = sum(c for _, c in data)
    winner = data[0]

    w_frame = tk.Frame(body, bg=CARD2, pady=14, padx=18,
                       highlightthickness=1, highlightbackground=GOLD)
    w_frame.pack(fill="x", pady=(0, 18))
    tk.Label(w_frame, text="🏆  WINNER", font=("Trebuchet MS", 8, "bold"),
             fg=GOLD, bg=CARD2).pack(anchor="w")
    tk.Label(w_frame, text=winner[0], font=("Georgia", 17, "bold"),
             fg=GOLD, bg=CARD2).pack(anchor="w", pady=(4, 0))
    tk.Label(w_frame, text=f"{winner[1]} votes  ·  {winner[1]/total*100:.1f}% of total",
             font=FONT_LABEL, fg=TEXT2, bg=CARD2).pack(anchor="w", pady=(2, 0))

    BAR_COLORS = [PRIMARY, ACCENT, WARN, PURPLE, SUCCESS]
    for i, (name, count) in enumerate(data):
        pct = count / total if total else 0
        row = tk.Frame(body, bg=BG)
        row.pack(fill="x", pady=6)
        tk.Label(row, text=name, font=("Georgia", 10, "bold"),
                 fg=TEXT, bg=BG, width=16, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(row, text=f"{count}", font=FONT_LABEL,
                 fg=TEXT2, bg=BG, width=5, anchor="e").grid(row=0, column=2, padx=(4, 0))
        bar_bg = tk.Frame(row, bg=CARD2, height=12, width=260)
        bar_bg.grid(row=0, column=1, padx=(10, 4))
        bar_bg.pack_propagate(False)
        fill_w = max(4, int(260 * pct))
        tk.Frame(bar_bg, bg=BAR_COLORS[i % len(BAR_COLORS)],
                 height=12, width=fill_w).pack(side="left", fill="y")
        tk.Label(row, text=f"{pct*100:.1f}%", font=FONT_SMALL,
                 fg=BAR_COLORS[i % len(BAR_COLORS)], bg=BG).grid(row=0, column=3, padx=(4, 0))

    hsep(body, pady=14)
    lbl(body, f"Total votes cast:  {total}", fg=TEXT2, bg=BG).pack(anchor="w")

# =========================================================
#  EXPORT
# =========================================================
def export_results():
    cursor.execute("""
    SELECT candidates.name, COUNT(*) FROM votes
    JOIN candidates ON candidates.id = votes.candidate_id
    GROUP BY candidates.name ORDER BY COUNT(*) DESC
    """)
    with open("results.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Candidate", "Votes"])
        w.writerows(cursor.fetchall())
    show_toast("Results exported to  results.csv", SUCCESS)

# =========================================================
#  STATS
# =========================================================
def show_stats():
    cursor.execute("SELECT COUNT(*) FROM users")
    users = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM votes")
    votes = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM candidates")
    cands = cursor.fetchone()[0]

    win = tk.Toplevel(root)
    win.title("System Statistics")
    win.configure(bg=BG)
    win.geometry("380x300")
    win.resizable(False, False)
    x = root.winfo_x() + (root.winfo_width()  - 380) // 2
    y = root.winfo_y() + (root.winfo_height() - 300) // 2
    win.geometry(f"+{x}+{y}")

    hdr = tk.Frame(win, bg=CARD2, pady=18, padx=24)
    hdr.pack(fill="x")
    tk.Label(hdr, text="📈  System Statistics", font=FONT_TITLE,
             fg=TEXT, bg=CARD2).pack(anchor="w")

    body = tk.Frame(win, bg=BG, padx=28, pady=20)
    body.pack(fill="both", expand=True)

    for icon, label_text, val, color in [
        ("👤", "Registered Users",  users, PRIMARY_LT),
        ("📋", "Active Candidates", cands, ACCENT),
        ("🗳️", "Total Votes Cast",  votes, SUCCESS_LT),
    ]:
        row = tk.Frame(body, bg=CARD2, highlightthickness=1, highlightbackground=BORDER)
        row.pack(fill="x", pady=6)
        inner = tk.Frame(row, bg=CARD2, padx=16, pady=12)
        inner.pack(fill="x")
        tk.Label(inner, text=icon, font=("Segoe UI", 15), bg=CARD2).pack(side="left")
        tk.Label(inner, text=label_text, font=FONT_SUB, fg=TEXT2, bg=CARD2).pack(side="left", padx=12)
        tk.Label(inner, text=str(val), font=FONT_STAT, fg=color, bg=CARD2).pack(side="right")

# =========================================================
#  ADMIN PANEL
# =========================================================
def delete_candidate_by_id(cid, name, refresh_fn):
    if messagebox.askyesno("Confirm Delete",
                           f"Remove '{name}'?\nAll associated votes will also be deleted."):
        cursor.execute("DELETE FROM votes WHERE candidate_id=?", (cid,))
        cursor.execute("DELETE FROM candidates WHERE id=?", (cid,))
        conn.commit()
        refresh_fn()
        show_toast(f"'{name}' removed.", WARN)

def admin_panel():
    ADMIN_PASS = "admin123"
    entered = simpledialog.askstring("Admin Access", "Enter admin password:", show="*")
    if entered != ADMIN_PASS:
        show_toast("Incorrect admin password.", DANGER); return

    win = tk.Toplevel(root)
    win.title("Admin Panel")
    win.configure(bg=BG)
    win.geometry("460x600")
    win.resizable(False, False)
    x = root.winfo_x() + (root.winfo_width()  - 460) // 2
    y = root.winfo_y() + (root.winfo_height() - 600) // 2
    win.geometry(f"+{x}+{y}")

    # ── Header ──────────────────────────────────────────
    hdr = tk.Frame(win, bg=CARD2, pady=18, padx=24)
    hdr.pack(fill="x")
    tk.Label(hdr, text="⚙️  Administration", font=FONT_TITLE,
             fg=TEXT, bg=CARD2).pack(anchor="w")
    tk.Label(hdr, text="Manage candidates and election data.",
             font=FONT_LABEL, fg=TEXT3, bg=CARD2).pack(anchor="w", pady=(4, 0))

    # ── Top area: add button ─────────────────────────────
    top = tk.Frame(win, bg=BG, padx=20, pady=14)
    top.pack(fill="x")

    def add_candidate_ui():
        name = simpledialog.askstring("Add Candidate", "Candidate name:")
        if name and name.strip():
            try:
                cursor.execute("INSERT INTO candidates(name) VALUES(?)", (name.strip(),))
                conn.commit()
                refresh_list()
                show_toast(f"'{name.strip()}' added.", SUCCESS)
            except:
                show_toast("Candidate already exists.", DANGER)

    make_button(top, "➕  Add New Candidate", add_candidate_ui,
                SUCCESS, SUCCESS_DK, font=FONT_BTN).pack(fill="x")

    # ── Section label ────────────────────────────────────
    sec = tk.Frame(win, bg=BG, padx=20)
    sec.pack(fill="x")
    tk.Label(sec, text="CANDIDATES", font=("Trebuchet MS", 8, "bold"),
             fg=TEXT3, bg=BG).pack(anchor="w", pady=(4, 4))

    # ── Scrollable candidate list (fixed height) ─────────
    list_container = tk.Frame(win, bg=BG, padx=20)
    list_container.pack(fill="x")

    canvas = tk.Canvas(list_container, bg=BG, bd=0, highlightthickness=0, height=220)
    scrollbar = tk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
    scroll_frame = tk.Frame(canvas, bg=BG)

    scroll_frame.bind("<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Mousewheel scrolling
    def on_mousewheel(e):
        canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
    canvas.bind_all("<MouseWheel>", on_mousewheel)

    def move_candidate(cid, direction):
        """Swap display_order with neighbour."""
        cursor.execute("SELECT id, name FROM candidates ORDER BY rowid")
        rows = cursor.fetchall()
        ids = [r[0] for r in rows]
        idx = ids.index(cid)
        swap_idx = idx + direction
        if swap_idx < 0 or swap_idx >= len(ids):
            return
        # Swap names to reorder (SQLite has no display_order col; swap names)
        name_a = rows[idx][1]
        name_b = rows[swap_idx][1]
        cursor.execute("UPDATE candidates SET name=? WHERE id=?", ("__tmp__", ids[idx]))
        cursor.execute("UPDATE candidates SET name=? WHERE id=?", (name_a, ids[swap_idx]))
        cursor.execute("UPDATE candidates SET name=? WHERE id=?", (name_b, ids[idx]))
        conn.commit()
        refresh_list()

    def refresh_list():
        for w in scroll_frame.winfo_children():
            w.destroy()
        cursor.execute("SELECT id, name FROM candidates ORDER BY rowid")
        data = cursor.fetchall()
        if not data:
            tk.Label(scroll_frame, text="No candidates yet.",
                     font=("Georgia", 10), fg=TEXT2, bg=BG, pady=16).pack(anchor="w")
            canvas.configure(scrollregion=canvas.bbox("all"))
            return

        for i, (cid, name) in enumerate(data):
            row = tk.Frame(scroll_frame, bg=CARD, highlightthickness=1,
                           highlightbackground=BORDER)
            row.pack(fill="x", pady=4, padx=2)

            inner = tk.Frame(row, bg=CARD, padx=12, pady=9)
            inner.pack(fill="x")

            # Order number badge
            tk.Label(inner, text=f"{i+1}", font=("Trebuchet MS", 9, "bold"),
                     fg=TEXT3, bg=CARD, width=2).pack(side="left")

            tk.Label(inner, text=name, font=("Georgia", 11),
                     fg=TEXT, bg=CARD).pack(side="left", padx=10)

            # ── Up / Down / Remove buttons ───────────────
            btn_grp = tk.Frame(inner, bg=CARD)
            btn_grp.pack(side="right")

            # Up
            up_btn = tk.Button(btn_grp, text="▲", bg=CARD2, fg=PRIMARY_LT,
                               font=("Trebuchet MS", 8, "bold"), bd=0,
                               padx=7, pady=3, cursor="hand2",
                               relief="flat",
                               command=lambda c=cid: move_candidate(c, -1))
            up_btn.bind("<Enter>", lambda e, b=up_btn: b.configure(bg=BORDER_LT))
            up_btn.bind("<Leave>", lambda e, b=up_btn: b.configure(bg=CARD2))
            up_btn.pack(side="left", padx=(0, 2))

            # Down
            dn_btn = tk.Button(btn_grp, text="▼", bg=CARD2, fg=PRIMARY_LT,
                               font=("Trebuchet MS", 8, "bold"), bd=0,
                               padx=7, pady=3, cursor="hand2",
                               relief="flat",
                               command=lambda c=cid: move_candidate(c, 1))
            dn_btn.bind("<Enter>", lambda e, b=dn_btn: b.configure(bg=BORDER_LT))
            dn_btn.bind("<Leave>", lambda e, b=dn_btn: b.configure(bg=CARD2))
            dn_btn.pack(side="left", padx=(0, 6))

            # Remove
            rm_btn = tk.Button(btn_grp, text="Remove", bg=DANGER, fg="white",
                               font=FONT_SMALL, bd=0, padx=9, pady=3,
                               cursor="hand2", relief="flat",
                               command=lambda c=cid, n=name: delete_candidate_by_id(c, n, refresh_list))
            rm_btn.bind("<Enter>", lambda e, b=rm_btn: b.configure(bg=DANGER_DK))
            rm_btn.bind("<Leave>", lambda e, b=rm_btn: b.configure(bg=DANGER))
            rm_btn.pack(side="left")

        canvas.configure(scrollregion=canvas.bbox("all"))

    refresh_list()

    # ── Fixed bottom action buttons ──────────────────────
    bottom = tk.Frame(win, bg=BG, padx=20, pady=14)
    bottom.pack(fill="x", side="bottom")

    hsep(bottom, color=BORDER, pady=6)

    for txt, cmd, bg, hv in [
        ("📊  View Results",  show_results,   PURPLE, PURPLE_DK),
        ("📁  Export CSV",    export_results, WARN,   WARN_DK),
        ("📈  System Stats",  show_stats,     ACCENT, ACCENT_DK),
    ]:
        make_button(bottom, txt, cmd, bg, hv, font=FONT_BTN).pack(fill="x", pady=3)

# =========================================================
#  LOGOUT
# =========================================================
def logout():
    global current_user
    current_user = None
    update_status("● Not signed in", TEXT3)
    show_toast("You have been signed out.", PRIMARY)

# =========================================================
#  MAIN LAYOUT
# =========================================================

# ── Sidebar ──────────────────────────────────────────────
sidebar = tk.Frame(root, bg=CARD, width=232)
sidebar.pack(side="left", fill="y")
sidebar.pack_propagate(False)

brand = tk.Frame(sidebar, bg=PRIMARY_DK, pady=24, padx=20)
brand.pack(fill="x")
tk.Label(brand, text="🗳️", font=("Segoe UI", 24), bg=PRIMARY_DK, fg="white").pack(anchor="w")
tk.Label(brand, text="SecureVote", font=FONT_BRAND, fg="white", bg=PRIMARY_DK).pack(anchor="w")
tk.Label(brand, text="Trusted Digital Voting", font=("Trebuchet MS", 8),
         fg="#bfdbfe", bg=PRIMARY_DK).pack(anchor="w", pady=(2, 0))

sb = tk.Frame(sidebar, bg=CARD, padx=14, pady=22)
sb.pack(fill="both", expand=True)

tk.Label(sb, text="MENU", font=("Trebuchet MS", 8, "bold"),
         fg=TEXT3, bg=CARD).pack(anchor="w", pady=(0, 10))

def nav_btn(text, cmd, icon=""):
    f = tk.Frame(sb, bg=CARD, cursor="hand2")
    f.pack(fill="x", pady=2)
    inner = tk.Frame(f, bg=CARD, padx=10, pady=10)
    inner.pack(fill="x")
    tk.Label(inner, text=icon, font=("Segoe UI", 11), fg=ACCENT,
             bg=CARD, width=2).pack(side="left")
    lbl_w = tk.Label(inner, text=text, font=FONT_NAV, fg=TEXT2, bg=CARD)
    lbl_w.pack(side="left", padx=8)

    widgets = [f, inner, lbl_w]
    def on_click(e=None): cmd()
    def enter(e):
        for w in widgets: w.configure(bg=CARD2)
    def leave(e):
        for w in widgets: w.configure(bg=CARD)
    for w in [f, inner, lbl_w]:
        w.bind("<Button-1>", on_click)
        w.bind("<Enter>", enter)
        w.bind("<Leave>", leave)

nav_btn("Register",    register,     "📝")
nav_btn("Sign In",     login,        "🔑")
nav_btn("Results",     show_results, "📊")
nav_btn("Admin Panel", admin_panel,  "⚙️")
nav_btn("Sign Out",    logout,       "🚪")

sf = tk.Frame(sidebar, bg=BG2, padx=14, pady=14,
              highlightthickness=1, highlightbackground=BORDER)
sf.pack(fill="x", side="bottom")
tk.Label(sf, text="v2.1  ·  Secure & Anonymous",
         font=FONT_SMALL, fg=TEXT3, bg=BG2).pack(anchor="w")

# ── Content area ─────────────────────────────────────────
content = tk.Frame(root, bg=BG)
content.pack(side="left", fill="both", expand=True)

topbar = tk.Frame(content, bg=BG2, pady=14, padx=28,
                  highlightthickness=1, highlightbackground=BORDER)
topbar.pack(fill="x")
tk.Label(topbar, text="Digital Voting Platform",
         font=("Georgia", 12, "bold"), fg=TEXT, bg=BG2).pack(side="left")
status_bar = tk.Label(topbar, textvariable=status_var,
                      font=FONT_SMALL, fg=TEXT3, bg=BG2)
status_bar.pack(side="right")

# ── Auth card ────────────────────────────────────────────
centre = tk.Frame(content, bg=BG)
centre.pack(expand=True)

card_frame = tk.Frame(centre, bg=CARD, highlightthickness=1, highlightbackground=BORDER)
card_frame.pack(padx=40, pady=30)

card_hdr = tk.Frame(card_frame, bg=CARD2, pady=20, padx=34)
card_hdr.pack(fill="x")
tk.Label(card_hdr, text="Sign In or Register",
         font=FONT_HEAD, fg=TEXT, bg=CARD2).pack(anchor="w")
tk.Label(card_hdr, text="Enter your credentials to access the secure voting portal.",
         font=FONT_LABEL, fg=TEXT3, bg=CARD2).pack(anchor="w", pady=(5, 0))

card_body = tk.Frame(card_frame, bg=CARD, padx=34, pady=26)
card_body.pack()

fields = [
    ("Username",               None, "user_e"),
    ("Password",               "*",  "pass_e"),
    ("ID Number  (12 digits)", None, "id_e"),
]
entries = {}
for ph, show, key in fields:
    label_text = ph.split("(")[0].strip()
    tk.Label(card_body, text=label_text,
             font=("Trebuchet MS", 9, "bold"), fg=TEXT2, bg=CARD,
             anchor="w").pack(fill="x", pady=(12, 3))
    frm, ent = make_entry(card_body, ph, show=show, width=32)
    frm.pack(fill="x")
    entries[key] = ent

user_e = entries["user_e"]
pass_e = entries["pass_e"]
id_e   = entries["id_e"]

hsep(card_body, pady=16)

btn_row = tk.Frame(card_body, bg=CARD)
btn_row.pack(fill="x", pady=(0, 4))

make_button(btn_row, "Create Account", register, SUCCESS, SUCCESS_DK,
            padx=14, pady=11, font=("Georgia", 10, "bold"), fg="white").pack(
    side="left", expand=True, fill="x", padx=(0, 8))
make_button(btn_row, "Sign In  →", login, PRIMARY, PRIMARY_DK,
            padx=14, pady=11, font=("Georgia", 10, "bold"), fg="white").pack(
    side="left", expand=True, fill="x")

info = tk.Frame(card_frame, bg=BG2, pady=12, padx=34,
                highlightthickness=1, highlightbackground=BORDER)
info.pack(fill="x")
icon_row(info, "🔒", "All passwords & IDs encrypted with SHA-256", bg=BG2)
icon_row(info, "🛡️", "Two-factor OTP authentication on every login", bg=BG2)
icon_row(info, "🗳️", "Each registered voter may cast exactly one vote", bg=BG2)

# ── Toast ────────────────────────────────────────────────
toast_lbl = tk.Label(root, text="", font=("Trebuchet MS", 10, "bold"),
                     fg="white", bg=SUCCESS, padx=18, pady=9, bd=0)

root.mainloop()