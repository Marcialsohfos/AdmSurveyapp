let currentDownloadUrl = '';
let currentFile = null; // Stockage global du fichier

console.log('✅ Script.js chargé avec succès');

// Gestion du drag and drop
const uploadArea = document.getElementById('uploadArea');
const fileInput = document.getElementById('fileInput');

if (uploadArea && fileInput) {
    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelection(e.target.files[0]);
        }
    });
}

function handleFileSelection(file) {
    console.log('📁 Fichier sélectionné:', file.name);
    console.log('📊 Type:', file.type);
    console.log('💾 Taille:', file.size, 'bytes');
    
    // Stocker le fichier globalement
    currentFile = file;
    
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'application/pdf', 'image/tiff'];
    if (!allowedTypes.includes(file.type)) {
        showError('Type de fichier non supporté.');
        return;
    }
    
    updateUploadArea(file.name);
    
    // Vérification de debug
    const fileInput = document.getElementById('fileInput');
    console.log('🔍 Fichiers dans input:', fileInput.files);
}

function updateUploadArea(filename) {
    // Mise à jour sécurisée sans perte de référence
    const uploadContent = uploadArea.querySelector('.upload-content');
    if (uploadContent) {
        uploadContent.innerHTML = `
            <i class="upload-icon">✅</i>
            <h3>Fichier sélectionné</h3>
            <p><strong>${filename}</strong></p>
            <button class="browse-btn" onclick="document.getElementById('fileInput').click()">
                Changer de fichier
            </button>
        `;
    } else {
        // Fallback si .upload-content n'existe pas
        uploadArea.innerHTML = `
            <div class="upload-content">
                <i class="upload-icon">✅</i>
                <h3>Fichier sélectionné</h3>
                <p><strong>${filename}</strong></p>
                <button class="browse-btn" onclick="document.getElementById('fileInput').click()">
                    Changer de fichier
                </button>
            </div>
        `;
    }
}

// FONCTION GLOBALE pour onclick
window.processFile = async function() {
    console.log('🎯 processFile() appelée via onclick!');
    
    // Vérification détaillée des fichiers
    const fileInput = document.getElementById('fileInput');
    console.log('🔍 fileInput:', fileInput);
    console.log('🔍 fileInput.files:', fileInput.files);
    console.log('🔍 fileInput.files.length:', fileInput.files ? fileInput.files.length : 'null');
    
    // Essayer d'abord le fichier global, puis l'input
    let fileToProcess = currentFile;
    
    if (!fileToProcess && fileInput && fileInput.files && fileInput.files.length > 0) {
        fileToProcess = fileInput.files[0];
        console.log('📁 Fichier récupéré depuis input:', fileToProcess.name);
    }
    
    if (!fileToProcess) {
        console.log('❌ Aucun fichier détecté');
        showError('Veuillez sélectionner un fichier');
        return;
    }
    
    console.log('✅ Fichier à traiter:', fileToProcess.name);
    
    const dataType = document.getElementById('dataType');
    const outputFormat = document.getElementById('outputFormat');
    
    if (!dataType || !outputFormat) {
        showError('Erreur de chargement de l\'interface');
        return;
    }
    
    const selectedDataType = dataType.value;
    const selectedOutputFormat = outputFormat.value;
    
    console.log('⚙️ Type de données:', selectedDataType);
    console.log('⚙️ Format de sortie:', selectedOutputFormat);
    
    const formData = new FormData();
    formData.append('file', fileToProcess);
    formData.append('data_type', selectedDataType);
    formData.append('format', selectedOutputFormat);
    
    showLoading();
    hideError();
    hideResults();
    
    try {
        console.log('📤 Envoi vers /upload...');
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        //Ajout
// Charger les types de données depuis l'API
async function loadDataTypes() {
    try {
        const response = await fetch('/api/data_types');
        const data = await response.json();
        
        const dataTypeSelect = document.getElementById('dataType');
        dataTypeSelect.innerHTML = '';
        
        data.data_types.forEach(type => {
            const option = document.createElement('option');
            option.value = type.id;
            option.textContent = type.name;
            dataTypeSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Erreur chargement types:', error);
    }
}

// Charger les formats depuis l'API  
async function loadFormats() {
    try {
        const response = await fetch('/api/formats');
        const data = await response.json();
        
        const formatSelect = document.getElementById('outputFormat');
        formatSelect.innerHTML = '';
        
        data.formats.forEach(format => {
            const option = document.createElement('option');
            option.value = format.id;
            option.textContent = format.name;
            formatSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Erreur chargement formats:', error);
    }
}

// Au chargement de la page
document.addEventListener('DOMContentLoaded', function() {
    loadDataTypes();
    loadFormats();
});
        console.log('📥 Statut réponse:', response.status);
        
        if (!response.ok) {
            throw new Error(`Erreur HTTP: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('📋 Résultat:', result);
        
        if (result.success) {
            console.log('✅ Succès du traitement');
            showResults(result.data);
            currentDownloadUrl = result.download_url;
            console.log('🔗 URL de téléchargement:', currentDownloadUrl);
        } else {
            console.log('❌ Erreur du serveur:', result.error);
            showError(result.error || 'Erreur du serveur');
        }
    } catch (error) {
        console.error('❌ Erreur complète:', error);
        showError('Erreur de connexion: ' + error.message);
    } finally {
        hideLoading();
    }
}

// Fonction de téléchargement globale
window.downloadFile = function() {
    console.log('📥 Téléchargement demandé, URL:', currentDownloadUrl);
    if (currentDownloadUrl) {
        window.open(currentDownloadUrl, '_blank');
    } else {
        showError('Aucun fichier à télécharger');
    }
}

function showResults(data) {
    console.log('📊 Affichage des résultats:', data);
    const resultsSection = document.getElementById('results');
    const extractedData = document.getElementById('extractedData');
    
    if (!resultsSection || !extractedData) {
        console.error('❌ Éléments de résultats non trouvés');
        return;
    }
    
    let formattedData = '';
    
    // Gestion des différents types de données
    if (data.type === 'universal') {
        formattedData = `📄 Type détecté: ${data.detected_type || 'Universal'}\n\n`;
        
        // Afficher le texte brut
        if (data.raw_text) {
            const preview = data.raw_text.substring(0, 500) + (data.raw_text.length > 500 ? '...' : '');
            formattedData += `Texte extrait (preview):\n${preview}\n\n`;
        }
        
        // Afficher les sections
        if (data.sections && data.sections.length > 0) {
            formattedData += `Sections détectées: ${data.sections.length}\n`;
            data.sections.slice(0, 3).forEach((section, idx) => {
                formattedData += `${idx + 1}. ${section.title || 'Sans titre'}\n`;
            });
        }
        
    } else if (data.type === 'budget') {
        formattedData = `💰 Total: ${data.total}€\n\n`;
        data.lignes_budgetaires.forEach(ligne => {
            formattedData += `${ligne.description}: ${ligne.montant}€\n`;
        });
    } else {
        // Fallback pour les autres types
        formattedData = '📄 Données extraites:\n' + JSON.stringify(data, null, 2);
    }
    
    extractedData.textContent = formattedData;
    resultsSection.style.display = 'block';
    console.log('✅ Résultats affichés');
}
function showLoading() {
    console.log('⏳ Affichage du loading...');
    const loading = document.getElementById('loading');
    const processBtn = document.getElementById('processBtn');
    
    if (loading) {
        loading.style.display = 'block';
        console.log('✅ Loading affiché');
    }
    if (processBtn) {
        processBtn.disabled = true;
        console.log('✅ Bouton désactivé');
    }
}

function hideLoading() {
    console.log('🏁 Masquage du loading...');
    const loading = document.getElementById('loading');
    const processBtn = document.getElementById('processBtn');
    
    if (loading) {
        loading.style.display = 'none';
        console.log('✅ Loading masqué');
    }
    if (processBtn) {
        processBtn.disabled = false;
        console.log('✅ Bouton réactivé');
    }
}

function showError(message) {
    console.error('🚨 Erreur:', message);
    const errorDiv = document.getElementById('error');
    if (errorDiv) {
        errorDiv.textContent = message;
        errorDiv.style.display = 'block';
        console.log('✅ Message d\'erreur affiché');
    }
}

function hideError() {
    const errorDiv = document.getElementById('error');
    if (errorDiv) {
        errorDiv.style.display = 'none';
        console.log('✅ Erreur masquée');
    }
}

function hideResults() {
    const resultsSection = document.getElementById('results');
    if (resultsSection) {
        resultsSection.style.display = 'none';
        console.log('✅ Résultats masqués');
    }
}

// Initialisation
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 SourceAdApp initialisé');
    console.log('🔍 processFile disponible:', typeof processFile);
    console.log('🔍 downloadFile disponible:', typeof downloadFile);
    
    // Vérification des éléments critiques
    console.log('🔍 processBtn:', document.getElementById('processBtn'));
    console.log('🔍 fileInput:', document.getElementById('fileInput'));
    console.log('🔍 dataType:', document.getElementById('dataType'));
    console.log('🔍 outputFormat:', document.getElementById('outputFormat'));
});