# DymoEtiquetes - Etiquetes per Quadre Elèctric

App per Windows per imprimir etiquetes a la **DYMO LetraTag LT-200B** amb
icones descarregades d'Internet.

## 🚀 Com generar el .exe (un sol cop)

### 1. Instal·la Python

Si no el tens, descarrega'l de: https://www.python.org/downloads/

⚠️ **IMPORTANT**: durant la instal·lació, marca la casella **"Add Python to PATH"**

### 2. Compila l'executable

Doble clic a **`compilar.bat`**

Trigarà 1-2 minuts. Quan acabi, tindràs:

```
DymoEtiquetes/
├── dist/
│   ├── DymoEtiquetes.exe    ← aquest és el teu executable
│   └── icones/               ← posa aquí les teves icones
```

Pots copiar la carpeta `dist` on vulguis (escriptori, USB, etc.) i executar
`DymoEtiquetes.exe` directament. Ja no et caldrà tenir Python per fer-lo servir.

---

## 🖨️ Com fer-lo servir

1. **Doble clic a `DymoEtiquetes.exe`**
2. Engega la impressora LT-200B (comprova que **NO** estigui connectada a cap mòbil)
3. Clica **🔌 Connectar**
4. Tria una icona de la llista (o clica **➕ Afegir fitxer** per carregar-ne una de qualsevol carpeta)
5. Escriu el text
6. Ajusta mida / invertir / llindar si cal
7. Clica **🖨️ IMPRIMIR**

## 📥 On descarregar icones

Busca icones **en blanc i negre, tipus silueta**, a:

- **SVG Repo** — https://www.svgrepo.com
- **Flaticon** — https://www.flaticon.com (cerca "electrical panel", "light bulb"...)
- **Icons8** — https://icons8.com
- **Google Fonts Icons** — https://fonts.google.com/icons
- **Google Imatges** — busca per exemple `"light bulb icon black silhouette png"`

Desa-les dins la carpeta `icones/` que hi ha al costat del .exe.
Formats admesos: PNG, JPG, WebP, BMP, GIF, SVG.

💡 **Consell**: com que la impressora només té 30 píxels d'alçada, les icones
amb molt detall es veuran com una taca. Busca **siluetes netes i simples**.

## ⚙️ Ajustos de la icona

- **Invertir colors**: actívalo si la icona és blanca sobre fons fosc
- **Llindar**: controla què es converteix en negre. Més baix = més píxels negres.
  Útil per icones amb línies fines o colors suaus.

## ❓ Resolució de problemes

### No troba la impressora
- Comprova que estigui engegada i amb piles carregades (4 × AA)
- El Bluetooth del PC ha d'estar actiu
- La impressora **no** ha d'estar connectada a cap mòbil. Si ho està, desaparella-la des de l'app DYMO Connect del mòbil
- Reinicia la impressora (apagar/engegar)

### L'antivirus bloqueja el .exe
Com que l'executable està generat amb PyInstaller, alguns antivirus donen falsos
positius. Afegeix-lo a excepcions o compila'l tu mateix amb `compilar.bat`
(així estàs segur que és el teu).

### La icona es veu malament
- Prova a baixar el llindar (30-80) si és massa clara
- Prova a pujar-lo (150-200) si queda massa tapada
- Marca "Invertir colors" si la icona original és blanca sobre negre
- Si res no funciona, busca una altra icona més simple

### Vull fer servir SVG
El .exe no inclou suport SVG per defecte (cal una llibreria extra).
Converteix els SVG a PNG primer amb qualsevol convertidor online,
o amb la pròpia SVG Repo que permet descarregar com a PNG.

## 📂 Estructura del projecte

```
DymoEtiquetes/
├── app.py              ← codi font de l'app
├── compilar.bat        ← script per generar el .exe
├── README.md           ← aquest fitxer
└── dist/               ← es crea en compilar
    ├── DymoEtiquetes.exe
    └── icones/
```
