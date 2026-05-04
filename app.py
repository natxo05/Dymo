"""
DYMO LetraTag - Aplicació moderna per imprimir etiquetes
amb icones descarregades d'Internet i tipografies personalitzables.

Executar des del codi:
    python app.py

Compilar a .exe:
    compilar.bat
"""

import sys
import os

# FIX per PyInstaller --windowed: stderr/stdout son None i algunes
# llibreries (com customtkinter) peten en intentar escriure-hi.
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")

import asyncio
import threading
from pathlib import Path
from tkinter import filedialog, messagebox, StringVar, IntVar

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageTk, ImageFilter

from dymo_bluetooth import discover_printers, Canvas


# ---------- CONFIGURACIÓ ----------
ALCADA_DEFAULT = 30     # Alçada per defecte (compatible amb app oficial DYMO)
ALCADA_MIN = 30         # Mínim segur
ALCADA_MAX = 72         # Màxim a provar (experimental)
STRETCH = 2
AMPLE_ICONA_RATIO = 1.07  # L'amplada de la icona = alçada × ratio

if hasattr(sys, '_MEIPASS'):
    BASE_DIR = Path(sys._MEIPASS)
    CARPETA_ICONES = Path(sys.executable).parent / "icones"
else:
    BASE_DIR = Path(__file__).parent
    CARPETA_ICONES = Path(__file__).parent / "icones"

CARPETA_ASSETS = BASE_DIR / "assets"

# Fonts típiques de Windows (nom_mostra, fitxer_ttf)
FONTS_RECOMANADES = [
    ("Arial Bold",        "arialbd.ttf"),
    ("Arial",             "arial.ttf"),
    ("Arial Black",       "ariblk.ttf"),
    ("Calibri Bold",      "calibrib.ttf"),
    ("Calibri",           "calibri.ttf"),
    ("Cambria Bold",      "cambriab.ttf"),
    ("Consolas Bold",     "consolab.ttf"),
    ("Consolas",          "consola.ttf"),
    ("Courier New Bold",  "courbd.ttf"),
    ("Courier New",       "cour.ttf"),
    ("Georgia Bold",      "georgiab.ttf"),
    ("Georgia",           "georgia.ttf"),
    ("Impact",            "impact.ttf"),
    ("Segoe UI Bold",     "seguisb.ttf"),
    ("Segoe UI",          "segoeui.ttf"),
    ("Segoe UI Black",    "seguibl.ttf"),
    ("Tahoma Bold",       "tahomabd.ttf"),
    ("Tahoma",            "tahoma.ttf"),
    ("Times Bold",        "timesbd.ttf"),
    ("Times New Roman",   "times.ttf"),
    ("Trebuchet Bold",    "trebucbd.ttf"),
    ("Trebuchet MS",      "trebuc.ttf"),
    ("Verdana Bold",      "verdanab.ttf"),
    ("Verdana",           "verdana.ttf"),
]

COLORS = {
    "accent":        "#3b82f6",
    "accent_hover":  "#2563eb",
    "success":       "#10b981",
    "success_hover": "#059669",
    "danger":        "#ef4444",
    "danger_hover":  "#dc2626",
    "warning":       "#f59e0b",
}


# ---------- CONVERSIÓ D'IMATGE ----------

def carrega_imatge(ruta: Path) -> Image.Image:
    if ruta.suffix.lower() == ".svg":
        try:
            import cairosvg, io
            png_bytes = cairosvg.svg2png(url=str(ruta), output_height=300)
            return Image.open(io.BytesIO(png_bytes)).convert("RGBA")
        except ImportError:
            raise RuntimeError("Per obrir SVG cal cairosvg.")
    return Image.open(ruta).convert("RGBA")


def icona_a_bn(img: Image.Image, alcada: int = ALCADA_DEFAULT,
               invertir: bool = False, llindar: int = 128) -> Image.Image:
    fons = Image.new("RGBA", img.size, (255, 255, 255, 255))
    fons.paste(img, (0, 0), img)
    img = fons.convert("L")
    if invertir:
        img = ImageOps.invert(img)
    w, h = img.size
    nova_ample = max(1, int(w * alcada / h))
    img = img.resize((nova_ample, alcada), Image.LANCZOS)
    img = img.point(lambda p: 0 if p < llindar else 255, mode="1")
    ample_max = int(alcada * AMPLE_ICONA_RATIO)
    if img.width > ample_max:
        esq = (img.width - ample_max) // 2
        img = img.crop((esq, 0, esq + ample_max, alcada))
    return img


def troba_fitxer_font(nom_fitxer: str) -> Path | None:
    candidates = [
        Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / nom_fitxer,
        Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts" / nom_fitxer,
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def carrega_font(nom_fitxer: str, mida: int) -> ImageFont.FreeTypeFont:
    ruta = troba_fitxer_font(nom_fitxer)
    if ruta:
        try:
            return ImageFont.truetype(str(ruta), mida)
        except Exception:
            pass
    try:
        return ImageFont.truetype(nom_fitxer, mida)
    except Exception:
        return ImageFont.load_default()


def crear_etiqueta(icona_img, text: str, mida_text: int = 40,
                   fitxer_font: str = "arialbd.ttf",
                   alcada: int = ALCADA_DEFAULT) -> Image.Image:
    font = carrega_font(fitxer_font, mida_text)

    dummy = Image.new("1", (1, 1), 1)
    ddraw = ImageDraw.Draw(dummy)
    bbox = ddraw.textbbox((0, 0), text, font=font)
    ample_text = bbox[2] - bbox[0]

    marge = 4
    ample_ic = (icona_img.width + marge) if icona_img else 0
    ample_total = max(60, ample_ic + ample_text + marge * 2)

    etiqueta = Image.new("1", (ample_total, alcada), 1)
    draw = ImageDraw.Draw(etiqueta)

    if icona_img:
        y_ic = (alcada - icona_img.height) // 2
        etiqueta.paste(icona_img, (marge, y_ic))

    y_text = (alcada - (bbox[3] - bbox[1])) // 2 - bbox[1]
    x_text = (ample_ic + marge) if icona_img else marge
    draw.text((x_text, y_text), text, fill=0, font=font)
    return etiqueta


def imatge_a_canvas(img: Image.Image) -> Canvas:
    canvas = Canvas()
    ample, alt = img.size
    for x in range(ample):
        for y in range(alt):
            if img.getpixel((x, y)) == 0:
                canvas.set_pixel(x, y, True)
    return canvas


# ---------- APP ----------

class DymoApp:
    def __init__(self):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("DYMO LetraTag · Editor d'etiquetes")
        self.root.geometry("1050x780")
        self.root.minsize(950, 700)

        # Icona de la finestra
        try:
            ico = CARPETA_ASSETS / "logo.ico"
            if ico.exists():
                self.root.iconbitmap(str(ico))
        except Exception:
            pass

        self.icona_original = None
        self.icona_bn = None
        self.ruta_icona = None
        self.printer = None
        self.loop = None
        self.alcada_actual = ALCADA_DEFAULT  # Alçada del bitmap a imprimir
        self.fonts_disponibles = self._descobreix_fonts()

        self._inicia_asyncio()
        if not CARPETA_ICONES.exists():
            CARPETA_ICONES.mkdir()

        self._construeix_ui()
        self._refresca_llista_icones()
        self._actualitza_preview()

    def _descobreix_fonts(self):
        disponibles = []
        for nom, fitxer in FONTS_RECOMANADES:
            if troba_fitxer_font(fitxer):
                disponibles.append((nom, fitxer))
        if not disponibles:
            disponibles = [("Per defecte", "arial.ttf")]
        return disponibles

    # ---- Async ----
    def _inicia_asyncio(self):
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_loop, daemon=True).start()

    def _run_loop(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def _tasca_async(self, coro, callback=None):
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        def quan_acabi():
            if future.done():
                try:
                    resultat = future.result()
                    if callback:
                        callback(resultat, None)
                except Exception as e:
                    if callback:
                        callback(None, e)
            else:
                self.root.after(100, quan_acabi)

        self.root.after(100, quan_acabi)

    # ---- UI ----
    def _construeix_ui(self):
        # HEADER
        header = ctk.CTkFrame(self.root, height=75, corner_radius=0,
                              fg_color=("#1e293b", "#0f172a"))
        header.pack(fill="x")
        header.pack_propagate(False)

        # Logo IPC (canvia segons el tema)
        self.logo_label = ctk.CTkLabel(header, text="")
        self.logo_label.pack(side="left", padx=(20, 10), pady=8)
        self._carrega_logo()

        titol_frame = ctk.CTkFrame(header, fg_color="transparent")
        titol_frame.pack(side="left", pady=12)

        ctk.CTkLabel(titol_frame, text="🏷️  DYMO LetraTag",
                     font=ctk.CTkFont(size=22, weight="bold"),
                     text_color="white").pack(anchor="w")
        ctk.CTkLabel(titol_frame, text="Editor d'etiquetes · LT-200B",
                     font=ctk.CTkFont(size=11),
                     text_color="#94a3b8").pack(anchor="w")

        dreta_header = ctk.CTkFrame(header, fg_color="transparent")
        dreta_header.pack(side="right", padx=20, pady=18)

        self.tema_switch = ctk.CTkSwitch(dreta_header, text="🌙",
                                          command=self._canvia_tema,
                                          width=50)
        self.tema_switch.pack(side="right", padx=(15, 0))
        self.tema_switch.select()

        self.estat_label = ctk.CTkLabel(dreta_header, text="● Desconnectada",
                                         text_color="#94a3b8",
                                         font=ctk.CTkFont(size=12))
        self.estat_label.pack(side="right", padx=15)

        self.btn_conn = ctk.CTkButton(dreta_header, text="Connectar",
                                       command=self.connectar,
                                       width=120, height=34,
                                       fg_color=COLORS["success"],
                                       hover_color=COLORS["success_hover"],
                                       font=ctk.CTkFont(size=13, weight="bold"),
                                       corner_radius=8)
        self.btn_conn.pack(side="right")

        # COS
        cos = ctk.CTkFrame(self.root, fg_color="transparent")
        cos.pack(fill="both", expand=True, padx=20, pady=20)
        cos.grid_columnconfigure(0, weight=1)
        cos.grid_columnconfigure(1, weight=2)
        cos.grid_rowconfigure(0, weight=1)

        # PANELL ESQUERRA
        panell_esq = ctk.CTkFrame(cos, corner_radius=12)
        panell_esq.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        ctk.CTkLabel(panell_esq, text="📁  ICONES",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 5))
        ctk.CTkLabel(panell_esq, text=f"Carpeta: {CARPETA_ICONES.name}/",
                     font=ctk.CTkFont(size=10),
                     text_color="gray").pack(anchor="w", padx=20)

        self.llista_frame = ctk.CTkScrollableFrame(panell_esq, corner_radius=8)
        self.llista_frame.pack(fill="both", expand=True, padx=15, pady=15)

        botons_icones = ctk.CTkFrame(panell_esq, fg_color="transparent")
        botons_icones.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkButton(botons_icones, text="📂", command=self._obrir_carpeta,
                      width=50, height=34).pack(side="left", padx=2)
        ctk.CTkButton(botons_icones, text="🔄", command=self._refresca_llista_icones,
                      width=50, height=34).pack(side="left", padx=2)
        ctk.CTkButton(botons_icones, text="➕ Afegir", command=self._afegir_fitxer,
                      height=34).pack(side="left", padx=2, fill="x", expand=True)
        ctk.CTkButton(botons_icones, text="❌", command=self._treu_icona,
                      width=50, height=34,
                      fg_color="transparent", border_width=1).pack(side="left", padx=2)

        # PANELL DRETA
        panell_dret = ctk.CTkScrollableFrame(cos, corner_radius=12)
        panell_dret.grid(row=0, column=1, sticky="nsew")

        # Text
        ctk.CTkLabel(panell_dret, text="✍️  TEXT",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 10))

        self.text_var = StringVar(value="Llum cuina")
        self.text_var.trace_add("write", lambda *_: self._actualitza_preview())
        ctk.CTkEntry(panell_dret, textvariable=self.text_var,
                     font=ctk.CTkFont(size=15), height=42, corner_radius=8,
                     placeholder_text="Escriu el text...").pack(
            fill="x", padx=20, pady=(0, 15))

        # Font
        font_frame = ctk.CTkFrame(panell_dret, fg_color="transparent")
        font_frame.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(font_frame, text="Tipografia:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w")

        noms_fonts = [n for n, _ in self.fonts_disponibles]
        self.font_var = StringVar(value=noms_fonts[0])
        ctk.CTkComboBox(font_frame, values=noms_fonts,
                        variable=self.font_var,
                        command=lambda _: self._actualitza_preview(),
                        height=38, corner_radius=8,
                        font=ctk.CTkFont(size=13),
                        state="readonly").pack(fill="x", pady=(5, 0))

        # Mida
        mida_frame = ctk.CTkFrame(panell_dret, fg_color="transparent")
        mida_frame.pack(fill="x", padx=20, pady=(15, 5))

        lbl_mida_header = ctk.CTkFrame(mida_frame, fg_color="transparent")
        lbl_mida_header.pack(fill="x")
        ctk.CTkLabel(lbl_mida_header, text="Mida del text:",
                     font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.mida_valor_lbl = ctk.CTkLabel(lbl_mida_header, text="35 px",
                                             text_color=COLORS["accent"],
                                             font=ctk.CTkFont(size=12, weight="bold"))
        self.mida_valor_lbl.pack(side="right")

        self.mida_var = IntVar(value=35)
        ctk.CTkSlider(mida_frame, from_=12, to=40,
                      variable=self.mida_var,
                      command=self._on_mida_canvia,
                      height=20).pack(fill="x", pady=5)

        # Ajustos icona
        ctk.CTkLabel(panell_dret, text="🎨  AJUSTOS DE LA ICONA",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 10))

        ajust_frame = ctk.CTkFrame(panell_dret, corner_radius=8)
        ajust_frame.pack(fill="x", padx=20, pady=5)

        self.invertir_var = IntVar(value=0)
        ctk.CTkCheckBox(ajust_frame,
                        text="Invertir colors (icones clares sobre fons fosc)",
                        variable=self.invertir_var,
                        command=self._reprocessa_icona,
                        font=ctk.CTkFont(size=12)).pack(
            anchor="w", padx=15, pady=(15, 10))

        llindar_header = ctk.CTkFrame(ajust_frame, fg_color="transparent")
        llindar_header.pack(fill="x", padx=15, pady=(5, 0))
        ctk.CTkLabel(llindar_header, text="Llindar (més baix = més negre):",
                     font=ctk.CTkFont(size=12)).pack(side="left")
        self.llindar_valor_lbl = ctk.CTkLabel(llindar_header, text="128",
                                                text_color=COLORS["accent"],
                                                font=ctk.CTkFont(size=12, weight="bold"))
        self.llindar_valor_lbl.pack(side="right")

        self.llindar_var = IntVar(value=128)
        ctk.CTkSlider(ajust_frame, from_=30, to=220,
                      variable=self.llindar_var,
                      command=self._on_llindar_canvia,
                      height=20).pack(fill="x", padx=15, pady=(5, 15))

        # Previsualització
        ctk.CTkLabel(panell_dret, text="👁️  PREVISUALITZACIÓ",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(
            anchor="w", padx=20, pady=(20, 10))

        preview_container = ctk.CTkFrame(panell_dret,
                                           fg_color=("#e5e7eb", "#1e293b"),
                                           corner_radius=12, height=220)
        preview_container.pack(fill="x", padx=20, pady=5)
        preview_container.pack_propagate(False)

        self.preview_label = ctk.CTkLabel(preview_container, text="")
        self.preview_label.pack(expand=True)

        self.preview_info = ctk.CTkLabel(panell_dret, text="",
                                           font=ctk.CTkFont(size=10),
                                           text_color="gray")
        self.preview_info.pack(padx=20, pady=(0, 10))

        # Botons d'acció
        acc_frame = ctk.CTkFrame(panell_dret, fg_color="transparent")
        acc_frame.pack(fill="x", padx=20, pady=(10, 20))

        self.btn_imprimir = ctk.CTkButton(acc_frame, text="🖨️   IMPRIMIR",
                                            command=self.imprimir,
                                            height=52,
                                            font=ctk.CTkFont(size=16, weight="bold"),
                                            fg_color=COLORS["danger"],
                                            hover_color=COLORS["danger_hover"],
                                            state="disabled",
                                            corner_radius=10)
        self.btn_imprimir.pack(fill="x", pady=(0, 8))

        ctk.CTkButton(acc_frame, text="💾 Desar com a PNG",
                      command=self.desar_png,
                      height=38, corner_radius=8,
                      fg_color="transparent", border_width=2).pack(fill="x")

    # ---- Handlers ----
    def _canvia_tema(self):
        mode = "dark" if self.tema_switch.get() else "light"
        ctk.set_appearance_mode(mode)
        self._carrega_logo()

    def _carrega_logo(self):
        """Carrega el logo IPC adequat segons el tema actiu."""
        try:
            mode_actual = ctk.get_appearance_mode()  # "Dark" o "Light"
            # En tema fosc fem servir el logo clar, i al revés
            if mode_actual.lower() == "dark":
                ruta = CARPETA_ASSETS / "logo_clar.png"
            else:
                ruta = CARPETA_ASSETS / "logo_fosc.png"

            if not ruta.exists():
                return

            img = Image.open(ruta).convert("RGBA")
            # Escalem mantenint proporció, alçada ~55 px
            ratio = 55 / img.height
            nou_w = int(img.width * ratio)
            img = img.resize((nou_w, 55), Image.LANCZOS)

            self.logo_img = ctk.CTkImage(light_image=img, dark_image=img,
                                          size=(nou_w, 55))
            self.logo_label.configure(image=self.logo_img)
        except Exception as e:
            # Si no es pot carregar el logo, no passa res, continuem
            pass

    def _on_mida_canvia(self, valor):
        self.mida_valor_lbl.configure(text=f"{int(float(valor))} px")
        self._actualitza_preview()

    def _on_llindar_canvia(self, valor):
        self.llindar_valor_lbl.configure(text=f"{int(float(valor))}")
        self._reprocessa_icona()

    def _refresca_llista_icones(self):
        for w in self.llista_frame.winfo_children():
            w.destroy()

        extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".svg", ".gif"}
        fitxers = sorted([f for f in CARPETA_ICONES.iterdir()
                          if f.is_file() and f.suffix.lower() in extensions])

        if not fitxers:
            ctk.CTkLabel(self.llista_frame,
                         text="📭\n\nCap icona a la carpeta\n\nClica 📂 per obrir-la",
                         font=ctk.CTkFont(size=11),
                         text_color="gray",
                         justify="center").pack(pady=30)
            return

        for f in fitxers:
            ctk.CTkButton(self.llista_frame,
                          text=f"  {f.name}",
                          command=lambda p=f: self._carrega_icona(p),
                          anchor="w", height=36, corner_radius=6,
                          fg_color="transparent", border_width=1,
                          hover_color=("#dbeafe", "#1e3a8a"),
                          font=ctk.CTkFont(size=12)).pack(fill="x", pady=2)

    def _obrir_carpeta(self):
        os.startfile(CARPETA_ICONES)

    def _afegir_fitxer(self):
        ruta = filedialog.askopenfilename(
            title="Tria una icona",
            filetypes=[("Imatges", "*.png *.jpg *.jpeg *.webp *.bmp *.svg *.gif"),
                       ("Tot", "*.*")]
        )
        if ruta:
            self._carrega_icona(Path(ruta))

    def _carrega_icona(self, ruta: Path):
        try:
            self.icona_original = carrega_imatge(ruta)
            self.ruta_icona = ruta
            self._reprocessa_icona()
        except Exception as e:
            messagebox.showerror("Error", f"No s'ha pogut carregar:\n{e}")

    def _reprocessa_icona(self):
        if self.icona_original is None:
            self._actualitza_preview()
            return
        self.icona_bn = icona_a_bn(
            self.icona_original,
            alcada=self.alcada_actual,
            invertir=bool(self.invertir_var.get()),
            llindar=self.llindar_var.get()
        )
        self._actualitza_preview()

    def _treu_icona(self):
        self.icona_original = None
        self.icona_bn = None
        self.ruta_icona = None
        self._actualitza_preview()

    def _fitxer_font_actual(self) -> str:
        nom_mostra = self.font_var.get()
        for nom, fitxer in self.fonts_disponibles:
            if nom == nom_mostra:
                return fitxer
        return "arialbd.ttf"

    def _actualitza_preview(self):
        text = self.text_var.get() or " "
        try:
            etiqueta = crear_etiqueta(self.icona_bn, text,
                                       mida_text=self.mida_var.get(),
                                       fitxer_font=self._fitxer_font_actual(),
                                       alcada=self.alcada_actual)
        except Exception:
            return

        # === Vista 1: PIXEL ART (fidel al que imprimira la maquina) ===
        max_w, max_h = 560, 50
        zoom_px = min(max_w / etiqueta.width, max_h / etiqueta.height)
        zoom_px = max(2, min(8, zoom_px))
        w1 = int(etiqueta.width * zoom_px)
        h1 = int(etiqueta.height * zoom_px)
        preview_px = etiqueta.convert("RGB").resize((w1, h1), Image.NEAREST)

        # === Vista 2: SIMULACIO CINTA REAL ===
        # Fem servir l'etiqueta en alta resolucio (re-renderitzada a mes DPI)
        # perque el text es vegi suau, i la posem sobre fons de "cinta"
        etiqueta_hires = self._crear_etiqueta_hires(text)
        # Ajustem la mida al mateix ample que la vista pixel art
        ratio = w1 / etiqueta_hires.width
        nova_h = int(etiqueta_hires.height * ratio)
        preview_suau = etiqueta_hires.resize((w1, nova_h), Image.LANCZOS)

        # Creem la "cinta" amb marges laterals i ombra
        marge_cinta = 20
        ample_cinta = w1 + marge_cinta * 2
        alt_cinta = nova_h + 20
        cinta = Image.new("RGB", (ample_cinta, alt_cinta), "#f8fafc")

        # Degradat subtil a la cinta (per files, molt mes rapid que pixel a pixel)
        for y in range(alt_cinta):
            t = y / alt_cinta
            r = int(255 - t * 25)
            g = int(255 - t * 20)
            b = int(255 - t * 15)
            draw_deg = ImageDraw.Draw(cinta)
            draw_deg.line([(0, y), (ample_cinta, y)], fill=(r, g, b))

        # Enganxem l'etiqueta centrada
        cinta.paste(preview_suau, (marge_cinta, (alt_cinta - nova_h) // 2))

        # Afegim forats laterals (com si fos cinta perforada)
        draw_cinta = ImageDraw.Draw(cinta)
        for x_forat in [8, ample_cinta - 12]:
            draw_cinta.ellipse(
                [x_forat, alt_cinta // 2 - 3,
                 x_forat + 5, alt_cinta // 2 + 2],
                fill="#cbd5e1"
            )

        # Ombra exterior
        ombra = Image.new("RGBA", (ample_cinta + 8, alt_cinta + 8),
                           (0, 0, 0, 0))
        ombra_draw = ImageDraw.Draw(ombra)
        ombra_draw.rectangle([4, 4, ample_cinta + 4, alt_cinta + 4],
                              fill=(0, 0, 0, 40))
        ombra = ombra.filter(ImageFilter.GaussianBlur(radius=3))

        composicio = Image.new("RGBA",
                                 (ample_cinta + 8, alt_cinta + 8),
                                 (0, 0, 0, 0))
        composicio.paste(ombra, (0, 0), ombra)
        composicio.paste(cinta, (2, 2))

        # === Combinem les dues vistes verticalment ===
        # Marc fi al pixel art
        preview_px_marc = ImageOps.expand(preview_px, border=1, fill="#475569")

        ample_total = max(preview_px_marc.width, composicio.width)
        alt_total = preview_px_marc.height + composicio.height + 10

        final = Image.new("RGBA", (ample_total, alt_total), (0, 0, 0, 0))
        # Vista cinta (a dalt, mes prominent)
        x_cinta = (ample_total - composicio.width) // 2
        final.paste(composicio, (x_cinta, 0), composicio)
        # Vista pixel art (a baix)
        x_px = (ample_total - preview_px_marc.width) // 2
        final.paste(preview_px_marc,
                     (x_px, composicio.height + 10))

        self.preview_tk = ImageTk.PhotoImage(final)
        self.preview_label.configure(image=self.preview_tk, text="")

        # Comprovem si el text supera l'alçada disponible
        try:
            font_check = carrega_font(self._fitxer_font_actual(),
                                       self.mida_var.get())
            dummy = Image.new("1", (1, 1), 1)
            ddraw = ImageDraw.Draw(dummy)
            bbox_check = ddraw.textbbox((0, 0), text, font=font_check)
            alt_text = bbox_check[3] - bbox_check[1]
            avis = ""
            if alt_text > self.alcada_actual - 2:
                avis = "  ⚠️  Text molt alt: pot quedar tallat per dalt/baix"
        except Exception:
            avis = ""

        self.preview_info.configure(
            text=f"Mida real: {etiqueta.width} × {etiqueta.height} px  ·  "
                 f"A dalt: simulació  ·  A baix: píxel real{avis}"
        )

    def _crear_etiqueta_hires(self, text: str, escala: int = 8) -> Image.Image:
        """Crea una versió d'alta resolució de l'etiqueta per veure-la suau.
        Renderitza directament amb una font gran (no escala píxels)."""
        fitxer_font = self._fitxer_font_actual()
        mida_real = self.mida_var.get()
        font_hires = carrega_font(fitxer_font, mida_real * escala)

        dummy = Image.new("RGB", (1, 1), "white")
        ddraw = ImageDraw.Draw(dummy)
        bbox = ddraw.textbbox((0, 0), text, font=font_hires)
        ample_text = bbox[2] - bbox[0]

        marge = 4 * escala
        alcada_hires = self.alcada_actual * escala

        # Icona: escalem amb smoothing
        icona_hires = None
        ample_ic = 0
        if self.icona_bn:
            ic = self.icona_bn.convert("L")
            nova_w = self.icona_bn.width * escala
            nova_h = self.icona_bn.height * escala
            # Smoothing lleuger
            icona_hires = ic.resize((nova_w, nova_h), Image.LANCZOS)
            ample_ic = nova_w + marge

        ample_total = max(60 * escala, ample_ic + ample_text + marge * 2)
        etiqueta = Image.new("RGB", (ample_total, alcada_hires), "white")
        draw = ImageDraw.Draw(etiqueta)

        if icona_hires:
            y_ic = (alcada_hires - icona_hires.height) // 2
            # Convertim a RGB i enganxem
            icona_rgb = Image.merge("RGB", (icona_hires,) * 3)
            etiqueta.paste(icona_rgb, (marge, y_ic))

        y_text = (alcada_hires - (bbox[3] - bbox[1])) // 2 - bbox[1]
        x_text = (ample_ic + marge) if icona_hires else marge
        draw.text((x_text, y_text), text, fill="black", font=font_hires)

        return etiqueta

    # ---- Impressora ----
    def connectar(self):
        self.btn_conn.configure(state="disabled", text="Buscant...")
        self.estat_label.configure(text="● Buscant...",
                                     text_color=COLORS["warning"])

        async def buscar():
            printers = await discover_printers()
            if not printers:
                return None
            p = printers[0]
            await p.connect()
            return p

        self._tasca_async(buscar(), self._quan_connectada)

    def _quan_connectada(self, printer, error):
        if error:
            self.estat_label.configure(text="● Error",
                                         text_color=COLORS["danger"])
            self.btn_conn.configure(state="normal", text="Reintentar")
            messagebox.showerror("Error de connexió",
                                 f"{error}\n\nComprova:\n"
                                 "• Impressora engegada\n"
                                 "• Bluetooth actiu\n"
                                 "• No connectada al mòbil")
            return

        if printer is None:
            self.estat_label.configure(text="● No trobada",
                                         text_color=COLORS["warning"])
            self.btn_conn.configure(state="normal", text="Reintentar")
            return

        self.printer = printer
        self.estat_label.configure(text="● Connectada",
                                     text_color=COLORS["success"])
        self.btn_conn.configure(state="normal", text="✓ Connectada")
        self.btn_imprimir.configure(state="normal")

    def imprimir(self):
        if not self.printer:
            messagebox.showwarning("Atenció", "Connecta't primer a la impressora.")
            return

        text = self.text_var.get().strip()
        if not text and self.icona_bn is None:
            messagebox.showwarning("Atenció", "Posa text o tria una icona.")
            return

        etiqueta = crear_etiqueta(self.icona_bn, text or " ",
                                   mida_text=self.mida_var.get(),
                                   fitxer_font=self._fitxer_font_actual(),
                                   alcada=self.alcada_actual)
        canvas = imatge_a_canvas(etiqueta)
        canvas = canvas.stretch(STRETCH)

        self.btn_imprimir.configure(state="disabled", text="Imprimint...")

        async def fer_print():
            return await self.printer.print(canvas)

        self._tasca_async(fer_print(), self._quan_imprès)

    def _quan_imprès(self, resultat, error):
        self.btn_imprimir.configure(state="normal", text="🖨️   IMPRIMIR")
        if error:
            messagebox.showerror("Error d'impressió", str(error))

    def desar_png(self):
        text = self.text_var.get().strip() or "etiqueta"
        etiqueta = crear_etiqueta(self.icona_bn, text,
                                   mida_text=self.mida_var.get(),
                                   fitxer_font=self._fitxer_font_actual(),
                                   alcada=self.alcada_actual)
        nom = filedialog.asksaveasfilename(
            defaultextension=".png",
            initialfile=f"{text.replace(' ', '_')}.png",
            filetypes=[("PNG", "*.png")]
        )
        if nom:
            etiqueta.save(nom)
            messagebox.showinfo("Desat", f"Guardat:\n{nom}")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = DymoApp()
    app.run()
