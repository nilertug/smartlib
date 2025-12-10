from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
import requests
import qrcode
from io import BytesIO

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///kutuphane.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Kitap(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    baslik = db.Column(db.String(200), nullable=False)
    yazar = db.Column(db.String(100))
    sayfa = db.Column(db.Integer)
    resim = db.Column(db.String(500))  # Kapak resmi URL'si
    durum = db.Column(db.String(50), default="Okunacak") # Okunacak, Okunuyor, Bitti
    puan = db.Column(db.Integer, default=0) # 5 üzerinden
    notlar = db.Column(db.Text, default="") # Senin notların

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    durum_filtresi = request.args.get('durum')
    if durum_filtresi:
        kitaplar = Kitap.query.filter_by(durum=durum_filtresi).all()
    else:
        kitaplar = Kitap.query.all()
    return render_template('index.html', kitaplar=kitaplar)

@app.route('/ara', methods=['GET', 'POST'])
def ara():
    sonuclar = []
    if request.method == 'POST':
        sorgu = request.form.get('sorgu')
        # Google Books API isteği
        url = f"https://www.googleapis.com/books/v1/volumes?q={sorgu}"
        cevap = requests.get(url)
        veri = cevap.json()
        
        if 'items' in veri:
            for item in veri['items']:
                bilgi = item['volumeInfo']
                # Verilerin eksik gelme ihtimaline karşı .get kullanıyoruz
                resim = bilgi.get('imageLinks', {}).get('thumbnail', 'https://via.placeholder.com/128x196?text=No+Cover')
                
                sonuclar.append({
                    'baslik': bilgi.get('title'),
                    'yazar': bilgi.get('authors', ['Bilinmiyor'])[0],
                    'sayfa': bilgi.get('pageCount', 0),
                    'resim': resim
                })
    return render_template('ara.html', sonuclar=sonuclar)

@app.route('/ekle', methods=['POST'])
def ekle():
    yeni_kitap = Kitap(
        baslik=request.form.get('baslik'),
        yazar=request.form.get('yazar'),
        sayfa=request.form.get('sayfa'),
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
    # Bu link arkadaşının göreceği link (Localhost iken sadece senin PC'de çalışır)
    # PythonAnywhere'e atınca burası otomatik olarak site adresin olacak.
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