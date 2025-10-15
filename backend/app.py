from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from ocr_processor import OCRProcessor
from data_converter import DataConverter

app = Flask(__name__, static_folder='static')
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'tiff'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

# ✅ CRÉATION DES DOSSIERS AU DÉMARRAGE
def create_required_folders():
    required_folders = [UPLOAD_FOLDER, 'converted', 'static']
    for folder in required_folders:
        os.makedirs(folder, exist_ok=True)
        print(f"✅ Dossier créé/vérifié: {folder}")

# Initialisation des processeurs
create_required_folders()  
ocr_processor = OCRProcessor()
data_converter = DataConverter()

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route pour la page principale
@app.route('/')
def serve_frontend():
    return send_from_directory('static', 'index.html')

# Route pour les fichiers statics (CSS, JS)
@app.route('/<path:filename>')
def serve_static_files(filename):
    return send_from_directory('static', filename)

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400
    
    file = request.files['file']
    data_type = request.form.get('data_type', 'auto')
    
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Traitement OCR
            print(f"🔍 Début du traitement OCR pour {filename}")
            extracted_data = ocr_processor.process_file(filepath, data_type)
            print(f"✅ OCR terminé, type détecté: {extracted_data.get('detected_type', 'unknown')}")
            
            # Conversion selon le format demandé
            output_format = request.form.get('format', 'csv')
            print(f"🔄 Conversion en format {output_format}")
            output_data = data_converter.convert_data(extracted_data, output_format)
            
            return jsonify({
                'success': True,
                'data': extracted_data,
                'download_url': f'/download/{output_data}',
                'detected_type': extracted_data.get('detected_type', 'unknown')
            })
            
        except Exception as e:
            print(f"❌ Erreur lors du traitement: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'error': f'Erreur de traitement: {str(e)}'}), 500
        finally:
            # Nettoyage du fichier uploadé
            try:
                if os.path.exists(filepath):
                    os.remove(filepath)
            except Exception as e:
                print(f"⚠️ Erreur lors du nettoyage: {e}")
    
    return jsonify({'error': 'Type de fichier non autorisé'}), 400

@app.route('/download/<filename>')
def download_converted_file(filename):
    try:
        return send_file(
            os.path.join('converted', filename),
            as_attachment=True,
            download_name=filename
        )
    except FileNotFoundError:
        return jsonify({'error': 'Fichier non trouvé'}), 404

# === ROUTES API UNIQUES (SUPPRIMEZ LES DOUBLONS) ===

@app.route('/api/data_types')
def get_available_data_types():
    """Route unique pour les types de données"""
    return jsonify({
        'data_types': [
            {'id': 'auto', 'name': '🔍 Détection automatique'},
            {'id': 'budget', 'name': '💰 Budget d\'investissement'},
            {'id': 'laboratoire', 'name': '🔬 Données Laboratoires'},
            {'id': 'voirie', 'name': '🛣️ Voirie et Réseaux Divers'},
            {'id': 'formation', 'name': '📚 Documents de formation'},
            {'id': 'legal', 'name': '⚖️ Documents juridiques'},
            {'id': 'administrative', 'name': '📋 Documents administratifs'},
            {'id': 'tabular', 'name': '📊 Données tabulaires'}
        ]
    })

@app.route('/api/formats')
def get_available_formats():
    """Route unique pour les formats de sortie"""
    return jsonify({
        'formats': [
            {'id': 'csv', 'name': 'CSV'},
            {'id': 'xlsx', 'name': 'Excel (.xlsx)'},
            {'id': 'json', 'name': 'JSON'},
            {'id': 'dta', 'name': 'Stata (.dta)'},
            {'id': 'sav', 'name': 'SPSS (.sav)'},
            {'id': 'shp', 'name': 'Shapefile (.shp)'},
            {'id': 'xml', 'name': 'XML'},
            {'id': 'html', 'name': 'HTML'},
            {'id': 'docx', 'name': 'Word (.docx)'},
            {'id': 'txt', 'name': 'Texte (.txt)'}
        ]
    })

@app.route('/health')
def health_check():
    return jsonify({
        "status": "healthy", 
        "message": "Backend SourceAdApp opérationnel",
        "endpoints": {
            "/upload": "POST - Upload de fichiers",
            "/api/data_types": "GET - Types de données disponibles",
            "/api/formats": "GET - Formats de sortie disponibles",
            "/download/<filename>": "GET - Téléchargement",
            "/health": "GET - Statut du serveur"
        }
    })

@app.route('/test')
def test_route():
    return jsonify({
        "message": "Test réussi!",
        "status": "operational"
    })
@app.route('/debug')
def debug_info():
    import os, subprocess
    info = {
        "working_directory": os.getcwd(),
        "files_in_wd": os.listdir('.'),
        "static_exists": os.path.exists('static'),
        "uploads_exists": os.path.exists('uploads'),
        "converted_exists": os.path.exists('converted'),
        "PORT": os.environ.get('PORT'),
        "tesseract_check": "Non testé"
    }
    
    # Test Tesseract
    try:
        result = subprocess.run(['which', 'tesseract'], capture_output=True, text=True)
        info["tesseract_check"] = result.stdout.strip() if result.stdout else "Non trouvé"
    except Exception as e:
        info["tesseract_check"] = f"Erreur: {e}"
    
    return jsonify(info)
@app.route('/test-ocr')
def test_ocr():
    import subprocess
    import tempfile
    from PIL import Image, ImageDraw
    import base64
    
    try:
        # Test 1: Vérification installation
        tesseract_version = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
        
        # Test 2: Création d'une image de test avec du texte
        img = Image.new('RGB', (400, 200), color='white')
        d = ImageDraw.Draw(img)
        d.text((50, 80), "TEST OCR SOURCEADAPP 2024", fill='black')
        
        # Sauvegarder temporairement
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp:
            img.save(tmp.name)
            
            # Test 3: Extraction OCR
            result = subprocess.run(['tesseract', tmp.name, 'stdout', '-l', 'fra'], 
                                  capture_output=True, text=True)
            
        return jsonify({
            'tesseract_installed': 'tesseract' in tesseract_version.stdout.lower(),
            'tesseract_version': tesseract_version.stdout,
            'ocr_test_result': result.stdout,
            'ocr_error': result.stderr,
            'test_image_created': True
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
@app.route('/debug-upload', methods=['POST'])
def debug_upload():
    """Route de débogage pour tester l'OCR"""
    if 'file' not in request.files:
        return jsonify({'error': 'Aucun fichier'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'Aucun fichier sélectionné'}), 400
    
    # Sauvegarder le fichier
    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    try:
        # Test OCR direct
        print(f"🔍 Test OCR pour {filename}")
        
        if filename.lower().endswith('.pdf'):
            # Conversion PDF
            images = pdf2image.convert_from_path(filepath, dpi=300)
            if images:
                first_page_text = self._extract_text_from_image(images[0])
                text = f"Page 1: {first_page_text}\n... ({len(images)} pages)"
            else:
                text = "Erreur conversion PDF"
        else:
            # Image directe
            text = self._extract_text_from_image(filepath)
        
        # Analyse des résultats
        result = {
            'filename': filename,
            'file_size': os.path.getsize(filepath),
            'text_length': len(text),
            'text_preview': text[:500] + '...' if len(text) > 500 else text,
            'ocr_success': len(text.strip()) > 10 and "aucun texte" not in text.lower()
        }
        
        return jsonify(result)
        
    except Exception as e:
        print(f"❌ Erreur debug: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Nettoyage
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    # Création des dossiers nécessaires
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs('converted', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    print(f"🚀 SourceAdApp démarré sur le port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
    