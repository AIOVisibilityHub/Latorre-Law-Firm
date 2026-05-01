#!/usr/bin/env python3
"""
Bilingual AI-crawlable public page builder
- Reads your existing index.html as the seed source when no JSON data exists.
- Generates English + Spanish pages with header/nav, language toggle, JSON-LD, llm.txt, sitemap.xml, and .nojekyll.
- Safe for GitHub Pages.
"""
import os, re, json, html
from datetime import date
from urllib.parse import urljoin

TODAY = date.today().isoformat()
YEAR = date.today().year

# ---------- helpers ----------
def esc(s):
    return html.escape(str(s or ''), quote=True)

def text_from_html(raw):
    raw = re.sub(r'<script[\s\S]*?</script>', ' ', raw, flags=re.I)
    raw = re.sub(r'<style[\s\S]*?</style>', ' ', raw, flags=re.I)
    raw = re.sub(r'<br\s*/?>', '\n', raw, flags=re.I)
    raw = re.sub(r'</p>|</h\d>|</li>', '\n', raw, flags=re.I)
    raw = re.sub(r'<[^>]+>', ' ', raw)
    return html.unescape(re.sub(r'[ \t]+', ' ', raw)).strip()

def first_match(pattern, raw, default=''):
    m = re.search(pattern, raw, flags=re.I|re.S)
    return html.unescape(re.sub(r'<[^>]+>', ' ', m.group(1)).strip()) if m else default

def load_json_file(path, default):
    if os.path.exists(path):
        try:
            with open(path, encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default
    return default

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def write(path, content):
    folder = os.path.dirname(path)
    if folder:
        ensure_dir(folder)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('✅ wrote', path)

# ---------- read seed ----------
seed_raw = ''
if os.path.exists('index.html'):
    with open('index.html', encoding='utf-8', errors='ignore') as f:
        seed_raw = f.read()

manifest = load_json_file('manifest.json', {})

seed_title = first_match(r'<title[^>]*>(.*?)</title>', seed_raw, '')
seed_h1 = first_match(r'<h1[^>]*>(.*?)</h1>', seed_raw, '')
seed_text = text_from_html(seed_raw)
phones = re.findall(r'(?:\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}', seed_text)

BUSINESS = manifest.get('businessName') or seed_h1 or seed_title.replace(' - Lawyer in Raleigh','') or 'Latorre Law Firm'
CANONICAL = (manifest.get('canonicalUrl') or manifest.get('websiteUrl') or '').rstrip('/')
if not CANONICAL:
    repo = os.getenv('GITHUB_REPOSITORY', '')
    CANONICAL = f'https://{repo.split("/")[0]}.github.io/{repo.split("/")[1]}' if '/' in repo else ''

PHONE_TOLL_FREE = manifest.get('phoneTollFree') or (phones[0] if phones else '(800) 966-6769')
PHONE_EN = manifest.get('phoneEnglish') or (phones[1] if len(phones) > 1 else '704-342-1111')
PHONE_ES = manifest.get('phoneSpanish') or (phones[2] if len(phones) > 2 else '704-344-0004')

ABOUT_EN = manifest.get('aboutEnglish') or (
    'Latorre Law Firm represents individuals and families in immigration, personal injury, workers compensation, and criminal defense matters. The firm serves clients throughout North Carolina, South Carolina, and Florida.'
)
ABOUT_ES = manifest.get('aboutSpanish') or (
    'Latorre Law Firm representa a individuos y familias en asuntos de inmigración, lesiones personales, compensación laboral y defensa criminal. La firma atiende a clientes en Carolina del Norte, Carolina del Sur y Florida.'
)

# Optional custom data: data/services.json can override these.
default_services = [
    {
        'en_title':'Auto Accident Injury',
        'es_title':'Accidentes de Auto',
        'en_terms':['Car accident injury','Rear-end collision','Intersection accident','Highway crash injury','Drunk driver accident'],
        'es_terms':['Accidente de carro','Choque por alcance','Accidente en intersección','Accidente en autopista','Accidente con conductor ebrio']
    },
    {
        'en_title':'Immigration Services',
        'es_title':'Servicios de Inmigración',
        'en_terms':['Green card application','Deportation defense','Asylum legal assistance','Family immigration petitions','Work permit assistance'],
        'es_terms':['Solicitud de residencia','Defensa contra deportación','Asilo','Peticiones familiares','Permiso de trabajo']
    },
    {
        'en_title':'Workers Compensation',
        'es_title':'Compensación Laboral',
        'en_terms':['Work injury claim','Denied workers compensation claim','Construction accident injury','Back injury at work'],
        'es_terms':['Reclamo por accidente de trabajo','Reclamo de compensación laboral negado','Accidente de construcción','Lesión de espalda en el trabajo']
    },
    {
        'en_title':'Criminal Defense',
        'es_title':'Defensa Criminal',
        'en_terms':['Criminal defense lawyer','DWI defense','Assault charge defense','Court representation'],
        'es_terms':['Abogado de defensa criminal','Defensa por DWI','Defensa por cargos de agresión','Representación en corte']
    }
]
SERVICES = load_json_file('data/services.json', default_services)
FAQS = load_json_file('data/faqs.json', [
    {'en_q':'What should I do after a car accident?', 'en_a':'Seek medical attention, document what happened, and contact an attorney before speaking in detail with an insurance company.', 'es_q':'¿Qué debo hacer después de un accidente de carro?', 'es_a':'Busque atención médica, documente lo ocurrido y contacte a un abogado antes de hablar en detalle con una compañía de seguros.'},
    {'en_q':'Can I apply for asylum?', 'en_a':'You may qualify depending on your circumstances, country conditions, deadlines, and supporting evidence.', 'es_q':'¿Puedo solicitar asilo?', 'es_a':'Puede calificar dependiendo de su situación, las condiciones de su país, los plazos y la evidencia disponible.'},
    {'en_q':'Do you help Spanish-speaking clients?', 'en_a':'Yes. The firm provides contact options for both English and Spanish-speaking clients.', 'es_q':'¿Ayudan a clientes que hablan español?', 'es_a':'Sí. La firma ofrece opciones de contacto para clientes que hablan inglés y español.'}
])

# ---------- page shell ----------
CSS = """
body{font-family:Arial,Helvetica,sans-serif;margin:0;color:#17202a;line-height:1.65;background:#fff}
.header{background:#102a43;color:white;padding:18px 24px}
.wrap{max-width:980px;margin:auto;padding:0 20px}
.brand{font-size:22px;font-weight:700;margin-bottom:10px}.nav{display:flex;gap:18px;flex-wrap:wrap;align-items:center}.nav a{color:white;text-decoration:none;font-weight:600}.lang{margin-left:auto;background:#f4b400;color:#111!important;padding:6px 10px;border-radius:6px}
.hero{background:#eef5fb;padding:44px 0;border-bottom:1px solid #d9e8f2}.hero h1{font-size:38px;line-height:1.15;margin:0 0 12px}.hero p{font-size:18px;margin:0;max-width:760px}
main{padding:34px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}.card{border:1px solid #dfe7ef;border-radius:12px;padding:20px;background:#fff;box-shadow:0 2px 8px rgba(0,0,0,.04)}h2{color:#102a43;margin-top:0}ul{padding-left:22px}.cta{background:#102a43;color:white;border-radius:12px;padding:24px;margin-top:28px}.cta a{color:white;font-weight:700}footer{border-top:1px solid #eee;margin-top:40px;padding:24px 0;color:#5f6c7b;font-size:14px}.small{font-size:14px;color:#5f6c7b}.contact-box p{margin:.35rem 0}
"""

def abs_url(path):
    if not CANONICAL:
        return path
    return CANONICAL + '/' + path.lstrip('/')

def nav(lang='en'):
    if lang == 'es':
        links = [('Inicio','/es/'),('Servicios','/es/services/'),('Preguntas','/es/faq/'),('Contacto','/es/contact/')]
        toggle = ('English','/')
    else:
        links = [('Home','/'),('Services','/services/'),('FAQ','/faq/'),('Contact','/contact/')]
        toggle = ('Español','/es/')
    return '<div class="header"><div class="wrap"><div class="brand">'+esc(BUSINESS)+'</div><div class="nav">' + ''.join(f'<a href="{href}">{label}</a>' for label,href in links) + f'<a class="lang" href="{toggle[1]}">{toggle[0]}</a></div></div></div>'

def jsonld(kind, lang):
    data = {
        '@context':'https://schema.org',
        '@type':'LegalService',
        'name': BUSINESS,
        'url': CANONICAL or '',
        'telephone': [PHONE_TOLL_FREE, PHONE_EN, PHONE_ES],
        'areaServed': ['North Carolina','South Carolina','Florida'],
        'availableLanguage': ['English','Spanish'],
        'knowsAbout': [s.get('en_title','') for s in SERVICES] + [s.get('es_title','') for s in SERVICES]
    }
    if kind == 'faq':
        data = {
            '@context':'https://schema.org',
            '@type':'FAQPage',
            'mainEntity':[{
                '@type':'Question',
                'name': f['es_q'] if lang == 'es' else f['en_q'],
                'acceptedAnswer':{'@type':'Answer','text': f['es_a'] if lang == 'es' else f['en_a']}
            } for f in FAQS]
        }
    return '<script type="application/ld+json">'+json.dumps(data, ensure_ascii=False)+'</script>'

def shell(title, desc, body, lang='en', path='/', kind='legal'):
    other = '/es/' if lang == 'en' else '/'
    return f'''<!DOCTYPE html>
<html lang="{lang}"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="alternate" hreflang="en" href="{esc(abs_url(path.replace('/es','',1) if path.startswith('/es') else path))}">
<link rel="alternate" hreflang="es" href="{esc(abs_url('/es' + (path if path != '/' else '/')))}">
<style>{CSS}</style>
{jsonld(kind, lang)}
</head><body>
{nav(lang)}
{body}
<footer><div class="wrap">© {YEAR} {esc(BUSINESS)} · Last updated {TODAY} · AI-crawlable bilingual public pages</div></footer>
</body></html>'''

def service_cards(lang='en'):
    cards=[]
    for s in SERVICES:
        title = s.get('es_title') if lang=='es' else s.get('en_title')
        terms = s.get('es_terms') if lang=='es' else s.get('en_terms')
        cards.append('<div class="card"><h2>'+esc(title)+'</h2><ul>'+''.join('<li>'+esc(t)+'</li>' for t in terms)+'</ul></div>')
    return '<div class="grid">'+''.join(cards)+'</div>'

def faq_cards(lang='en'):
    cards=[]
    for f in FAQS:
        q = f['es_q'] if lang=='es' else f['en_q']
        a = f['es_a'] if lang=='es' else f['en_a']
        cards.append('<div class="card"><h2>'+esc(q)+'</h2><p>'+esc(a)+'</p></div>')
    return ''.join(cards)

def contact_block(lang='en'):
    labels = ('Línea gratuita','Inglés','Español','Estamos disponibles para ayudarle a entender sus opciones.') if lang=='es' else ('Toll-free','English','Español','We are available to help you understand your options.')
    return f'''<div class="card contact-box"><h2>{'Contáctenos' if lang=='es' else 'Contact Us'}</h2>
<p><strong>{labels[0]}:</strong> {esc(PHONE_TOLL_FREE)}</p><p><strong>{labels[1]}:</strong> {esc(PHONE_EN)}</p><p><strong>{labels[2]}:</strong> {esc(PHONE_ES)}</p><p>{esc(labels[3])}</p></div>'''

# ---------- build pages ----------
def build_home(lang='en'):
    is_es = lang == 'es'
    title = ('Abogados de Inmigración y Lesiones | ' if is_es else 'Immigration & Injury Lawyers | ') + BUSINESS
    desc = (ABOUT_ES if is_es else ABOUT_EN)[:155]
    h1 = 'Abogados de Inmigración y Lesiones' if is_es else 'Immigration & Injury Lawyers'
    intro = ABOUT_ES if is_es else ABOUT_EN
    path = '/es/' if is_es else '/'
    body = f'''<section class="hero"><div class="wrap"><h1>{esc(h1)}</h1><p>{esc(intro)}</p></div></section><main><div class="wrap">
<h2>{'Servicios basados en cómo las personas buscan ayuda' if is_es else 'Services Based on How People Actually Search for Help'}</h2>
{service_cards(lang)}
<div class="cta"><h2>{'¿Necesita ayuda?' if is_es else 'Need Help?'}</h2>{contact_block(lang)}</div>
</div></main>'''
    write('es/index.html' if is_es else 'index.html', shell(title, desc, body, lang, path))

def build_services(lang='en'):
    is_es = lang == 'es'
    title = ('Servicios Legales | ' if is_es else 'Legal Services | ') + BUSINESS
    desc = 'Servicios legales en inglés y español.' if is_es else 'English and Spanish legal services structured by real client search behavior.'
    path = '/es/services/' if is_es else '/services/'
    body = f'''<section class="hero"><div class="wrap"><h1>{'Servicios Legales' if is_es else 'Legal Services'}</h1><p>{'Organizados por las palabras que usan los clientes reales.' if is_es else 'Organized around the words real clients use when searching for help.'}</p></div></section><main><div class="wrap">{service_cards(lang)}</div></main>'''
    out = 'es/services/index.html' if is_es else 'services/index.html'
    write(out, shell(title, desc, body, lang, path))
    # compatibility URL
    write('es/services.html' if is_es else 'services.html', shell(title, desc, body, lang, path))

def build_faq(lang='en'):
    is_es = lang == 'es'
    title = ('Preguntas Frecuentes | ' if is_es else 'Frequently Asked Questions | ') + BUSINESS
    desc = 'Preguntas frecuentes para clientes legales.' if is_es else 'Frequently asked questions for legal clients.'
    path = '/es/faq/' if is_es else '/faq/'
    body = f'''<section class="hero"><div class="wrap"><h1>{'Preguntas Frecuentes' if is_es else 'Frequently Asked Questions'}</h1><p>{'Respuestas claras para personas que buscan ayuda legal.' if is_es else 'Clear answers for people searching for legal help.'}</p></div></section><main><div class="wrap">{faq_cards(lang)}</div></main>'''
    write('es/faq/index.html' if is_es else 'faq/index.html', shell(title, desc, body, lang, path, 'faq'))
    write('es/faq.html' if is_es else 'faq.html', shell(title, desc, body, lang, path, 'faq'))

def build_contact(lang='en'):
    is_es = lang == 'es'
    title = ('Contáctenos | ' if is_es else 'Contact Us | ') + BUSINESS
    desc = 'Información de contacto.' if is_es else 'Contact information.'
    path = '/es/contact/' if is_es else '/contact/'
    body = f'''<section class="hero"><div class="wrap"><h1>{'Contáctenos' if is_es else 'Contact Us'}</h1><p>{'Comuníquese con la firma en inglés o español.' if is_es else 'Contact the firm in English or Spanish.'}</p></div></section><main><div class="wrap">{contact_block(lang)}</div></main>'''
    write('es/contact/index.html' if is_es else 'contact/index.html', shell(title, desc, body, lang, path))
    write('es/contact.html' if is_es else 'contact.html', shell(title, desc, body, lang, path))

def build_llm_and_sitemap():
    urls = ['/', '/services/', '/faq/', '/contact/', '/es/', '/es/services/', '/es/faq/', '/es/contact/']
    llm = f'''# {BUSINESS}\n\n{ABOUT_EN}\n\nSpanish summary:\n{ABOUT_ES}\n\nLanguages:\n- English\n- Spanish\n\nPrimary services:\n''' + ''.join(f'- {s.get("en_title")} / {s.get("es_title")}\n' for s in SERVICES) + '\nKey pages:\n' + ''.join(f'- {abs_url(u)}\n' for u in urls)
    write('llm.txt', llm)
    sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        sm += f'  <url><loc>{esc(abs_url(u))}</loc><lastmod>{TODAY}</lastmod></url>\n'
    sm += '</urlset>\n'
    write('sitemap.xml', sm)
    write('.nojekyll', '')

if __name__ == '__main__':
    print('STARTING bilingual public page build')
    for lang in ['en','es']:
        build_home(lang)
        build_services(lang)
        build_faq(lang)
        build_contact(lang)
    build_llm_and_sitemap()
    print('BUILD COMPLETE')
