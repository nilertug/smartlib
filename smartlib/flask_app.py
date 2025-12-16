from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
import requests
import qrcode
from io import BytesIO
import random 

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kutuphane.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Kitap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    yazar = db.Column(db.String(100))
    sayfa = db.Column(db.Integer)
    resim = db.Column(db.String(500))
    durum = db.Column(db.String(50), default="Okunacak") 
    puan = db.Column(db.Integer, default=0) 
    notlar = db.Column(db.Text, default="") 

with app.app_context():
    db.create_all()


def get_weather(city="Ankara"):
    url = "https://api.open-meteo.com/v1/forecast?latitude=39.93&longitude=32.85&current_weather=true"
    
    try:
        response = requests.get(url, timeout=5) 
        data = response.json()
        
        wmo_code = data['current_weather']['weathercode']
        temp = data['current_weather']['temperature']
        
        condition = "Clear"
        
        if wmo_code == 0:
            condition = "Clear"
        elif wmo_code in [1, 2, 3, 45, 48]:
            condition = "Clouds"
        elif wmo_code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
            condition = "Rain"
        elif wmo_code >= 71:
            condition = "Snow"
            
        return condition, temp
        
    except:
        
        return "Clear", 20 

def get_book_recommendations(weather_condition):
    weather_to_genre = {
        "Clear":  ["subject:humor", "subject:travel", "subject:romance"], 
        "Rain":   ["subject:mystery", "subject:thriller", "subject:poetry"], 
        "Clouds": ["subject:philosophy", "subject:psychology", "subject:fiction"], 
        "Snow":   ["subject:fantasy", "subject:history", "subject:classics"], 
    }
    
    selected_genres = weather_to_genre.get(weather_condition, weather_to_genre["Clouds"])
    search_query = random.choice(selected_genres)
    
    url = f"https://www.googleapis.com/books/v1/volumes?q={search_query}&maxResults=3&langRestrict=tr"
    
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        items = data.get("items", [])
        
        oneriler = []
        for item in items:
            info = item['volumeInfo']
            resim = info.get('imageLinks', {}).get('thumbnail', 'https://via.placeholder.com/128x196?text=No+Cover')
            oneriler.append({
                'baslik': info.get('title'),
                'yazar': info.get('authors', ['Bilinmiyor'])[0],
                'resim': resim,
                'link': info.get('previewLink', '#')
            })
        
        tur_adi = search_query.split(':')[1].capitalize()
        return oneriler, tur_adi
    except:
        return [], "Genel"

@app.route('/')
def index():
    durum_filtresi = request.args.get('durum')
    if durum_filtresi:
        kitaplar = Kitap.query.filter_by(durum=durum_filtresi).all()
    else:
        kitaplar = Kitap.query.all()
    
    # Hava durumu ve önerileri al
    hava_durumu, sicaklik = get_weather("Ankara")
    oneriler, secilen_tur = get_book_recommendations(hava_durumu)

    return render_template('index.html', kitaplar=kitaplar, oneriler=oneriler, hava=hava_durumu, sicaklik=sicaklik, tur=secilen_tur)

@app.route('/ara', methods=['GET', 'POST'])
def ara():
    sonuclar = []
    if request.method == 'POST':
        sorgu = request.form.get('sorgu')
        url = f"https://www.googleapis.com/books/v1/volumes?q={sorgu}"
        try:
            cevap = requests.get(url)
            veri = cevap.json()
            if 'items' in veri:
                for item in veri['items']:
                    bilgi = item['volumeInfo']
                    resim = bilgi.get('imageLinks', {}).get('thumbnail', 'https://via.placeholder.com/128x196?text=No+Cover')
                    sonuclar.append({
                        'baslik': bilgi.get('title'),
                        'yazar': bilgi.get('authors', ['Bilinmiyor'])[0],
                        'sayfa': bilgi.get('pageCount', 0),
                        'resim': resim
                    })
        except:
            pass
    return render_template('ara.html', sonuclar=sonuclar)

@app.route('/ekle', methods=['POST'])
def ekle():
    yeni_kitap = Kitap(
        baslik=request.form.get('baslik'),
        yazar=request.form.get('yazar'),
        sayfa=request.form.get('sayfa', 0), 
        resim=request.form.get('resim')
    )
    db.session.add(yeni_kitap)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/detay/<int:id>', methods=['GET', 'POST'])
def detay(id):
    kitap = Kitap.query.get_or_404(id)
    if request.method == 'POST':
        kitap.durum = request.form.get('durum')
        kitap.puan = request.form.get('puan')
        kitap.notlar = request.form.get('notlar')
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('detay.html', kitap=kitap)

@app.route('/sil/<int:id>')
def sil(id):
    kitap = Kitap.query.get_or_404(id)
    db.session.delete(kitap)
    db.session.commit()
    return redirect(url_for('index'))

@app.route('/qr_uret/<int:id>')
def qr_uret(id):
    link = url_for('paylasim', id=id, _external=True)
    img = qrcode.make(link)
    buf = BytesIO()
    img.save(buf)
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

@app.route('/paylas/<int:id>')
def paylasim(id):
    kitap = Kitap.query.get_or_404(id)
    return render_template('paylasim.html', kitap=kitap)

if __name__ == '__main__':
    app.run(debug=True)

