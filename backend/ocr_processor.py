import pytesseract
from PIL import Image
import cv2
import numpy as np
import pdf2image
import re
from typing import Dict, List, Any, Optional

class OCRProcessor:
 def __init__(self):
    # Configuration Tesseract pour Render/Linux
    try:
        # Sur Render, Tesseract est généralement dans le PATH
        # Teste si tesseract est disponible
        import subprocess
        result = subprocess.run(['which', 'tesseract'], capture_output=True, text=True)
        if result.stdout:
            print(f"✅ Tesseract trouvé: {result.stdout.strip()}")
        else:
            print("⚠️ Tesseract non trouvé dans le PATH")
            # Essaye les chemins communs Linux
            possible_paths = [
                '/usr/bin/tesseract',
                '/usr/local/bin/tesseract',
                '/app/.apt/usr/bin/tesseract'
            ]
            for path in possible_paths:
                import os
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"✅ Tesseract configuré: {path}")
                    break
    except Exception as e:
        print(f"⚠️ Configuration Tesseract échouée: {e}")
        # Continue sans configuration spécifique
        
        # Parsers spécialisés par type de contenu
        self.specialized_parsers = {
            'budget': self._parse_budget_data,
            'laboratoire': self._parse_lab_data,
            'rh_laboratoire': self._parse_rh_data,
            'voirie': self._parse_voirie_data,
            'formation': self._parse_formation_data,
            'tabular': self._parse_tabular_data_enhanced,
            'legal': self._parse_legal_data,
            'administrative': self._parse_administrative_data,
        }
        
        # Détecteurs automatiques de type
        self.content_detectors = [
            self._detect_budget,
            self._detect_formation,
            self._detect_tabular,
            self._detect_legal,
            self._detect_administrative,
            self._detect_rh_laboratoire
        ]
    
    def process_file(self, filepath: str, data_type: str = 'auto') -> Dict[str, Any]:
        """Traite le fichier avec détection automatique ou manuelle du type"""
        # Extraction OCR
        text = self._extract_text(filepath)
        print(f"📝 Texte extrait ({len(text)} caractères)")
        
        # Détection automatique si demandé
        if data_type == 'auto':
            detected_type = self._auto_detect_content_type(text)
            print(f"🔍 Type détecté: {detected_type}")
            
            # Utiliser le parser tabulaire amélioré si détecté
            if detected_type == 'tabular':
                parser = self._parse_tabular_data_enhanced
            else:
                parser = self.specialized_parsers.get(detected_type, self._parse_universal)
            data_type = detected_type
        else:
            # Utiliser le parser spécifié
            if data_type == 'tabular':
                parser = self._parse_tabular_data_enhanced
            else:
                parser = self.specialized_parsers.get(data_type, self._parse_universal)
        
        # Parsing
        parsed_data = parser(text)
        parsed_data['detected_type'] = data_type
        parsed_data['raw_text_preview'] = text[:500] + '...' if len(text) > 500 else text
        
        # Log des résultats
        if 'tables' in parsed_data:
            print(f"📊 Tableaux détectés: {len(parsed_data['tables'])}")
            for i, table in enumerate(parsed_data['tables']):
                print(f"  - Tableau {i+1}: {table.get('row_count', 0)} lignes x {table.get('column_count', 0)} colonnes")
        
        return parsed_data
    
    def _auto_detect_content_type(self, text: str) -> str:
        """Détecte automatiquement le type de contenu"""
        scores = {}
        
        for detector in self.content_detectors:
            detector_name, score = detector(text)
            scores[detector_name] = score
        
        # Retourne le type avec le score le plus élevé
        best_type = max(scores.items(), key=lambda x: x[1])[0]
        return best_type if scores[best_type] > 0 else 'universal'
    
    def _detect_budget(self, text: str) -> tuple:
        """Détecte les documents budgétaires"""
        keywords = ['budget', 'montant', 'euro', '€', 'total', 'dépense', 'recette', 'solde', 'finance']
        score = sum(1 for kw in keywords if kw in text.lower())
        return 'budget', score
    
    def _detect_formation(self, text: str) -> tuple:
        """Détecte les documents de formation"""
        keywords = ['exercice', 'question', 'réponse', 'évaluation', 'formation', 'apprentissage', 'examen', 'test']
        score = sum(1 for kw in keywords if kw in text.lower())
        return 'formation', score
    
    def _detect_tabular(self, text: str) -> tuple:
        """Détecte les données tabulaires"""
        # Compte les lignes avec des séparateurs tabulaires
        lines = text.split('\n')
        if not lines:
            return 'tabular', 0
            
        tabular_lines = sum(1 for line in lines 
                          if re.search(r'\s{2,}|\t|\|', line) and len(line.split()) >= 2)
        return 'tabular', tabular_lines / len(lines)
    
    def _detect_legal(self, text: str) -> tuple:
        """Détecte les documents juridiques"""
        keywords = ['article', 'loi', 'décret', 'juridique', 'contrat', 'clause', 'legal', 'code']
        score = sum(1 for kw in keywords if kw in text.lower())
        return 'legal', score
    
    def _detect_administrative(self, text: str) -> tuple:
        """Détecte les documents administratifs génériques"""
        keywords = ['référence', 'objet', 'destinataire', 'expéditeur', 'administration', 'document', 'officiel']
        score = sum(1 for kw in keywords if kw in text.lower())
        return 'administrative', score
    
    def _detect_rh_laboratoire(self, text: str) -> tuple:
        """Détecte les données RH de laboratoire"""
        keywords = ['technicien', 'atms', 'tms', 'tpms', 'itms', 'ims', 'effectif', 'grade', 'personnel', 'laboratoire']
        score = sum(1 for kw in keywords if kw in text.lower())
        return 'rh_laboratoire', score
    
    def _parse_universal(self, text: str) -> Dict[str, Any]:
        """
        Parser universel pour tout type de document
        Structure intelligente basée sur l'analyse du contenu
        """
        # Vérifier si du texte a été extrait
        if not text or text.strip() in ["Aucun texte détecté dans l'image", "Erreur lors de l'extraction OCR"]:
            return {
                'type': 'universal',
                'metadata': {'error': 'Aucun texte extrait'},
                'structure': {'error': 'OCR a échoué'},
                'entities': {},
                'sections': [],
                'tables': [],
                'raw_text': text if text else 'Aucun texte extrait par OCR',
                'ocr_success': False
            }
        
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        return {
            'type': 'universal',
            'metadata': self._extract_metadata(text),
            'structure': self._analyze_document_structure(lines),
            'entities': self._extract_entities(text),
            'sections': self._extract_semantic_sections(lines),
            'tables': self._extract_tabular_data(lines),
            'raw_text': text,
            'ocr_success': True,
            'text_length': len(text),
            'line_count': len(lines)
        }
    
    def _parse_formation_data(self, text: str) -> Dict[str, Any]:
        """Parse les documents de formation/évaluation structurés"""
        data = {
            'type': 'formation',
            'titre': '',
            'date': '',
            'exercices': [],
            'questions': [],
            'instructions': []
        }
        
        lines = text.split('\n')
        current_section = None
        current_exercice = None
        current_question = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Détection du titre
            if 'INSTITUT' in line or 'MASTER' in line or 'FORMATION' in line:
                data['titre'] = line
                continue
                
            # Détection de la date
            date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', line)
            if date_match and not data['date']:
                data['date'] = date_match.group(1)
                
            # Détection des exercices
            if 'Exercice' in line or 'EXERCICE' in line:
                current_exercice = {
                    'titre': line,
                    'description': '',
                    'questions': []
                }
                data['exercices'].append(current_exercice)
                current_section = 'exercice'
                continue
                
            # Détection des questions (A., B., C., etc.)
            question_match = re.match(r'^([A-Z])\.\s*(.*)$', line)
            if question_match:
                current_question = {
                    'lettre': question_match.group(1),
                    'texte': question_match.group(2),
                    'instructions': []
                }
                if current_exercice:
                    current_exercice['questions'].append(current_question)
                else:
                    data['questions'].append(current_question)
                current_section = 'question'
                continue
                
            # Détection des instructions
            if 'Instructions' in line or 'INSTRUCTIONS' in line:
                current_section = 'instructions'
                continue
                
            # Ajout du contenu selon la section
            if current_section == 'exercice' and current_exercice:
                current_exercice['description'] += line + ' '
            elif current_section == 'question' and current_question:
                current_question['texte'] += ' ' + line
            elif current_section == 'instructions':
                data['instructions'].append(line)
            elif not current_section and len(line) > 10:
                # Texte général
                data['instructions'].append(line)
        
        return data
    
    def _parse_tabular_data_enhanced(self, text: str) -> Dict[str, Any]:
        """Parse amélioré pour les données tabulaires avec détection de tableaux"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        data = {
            'type': 'tabular',
            'tables': [],
            'raw_data': [],
            'metadata': {}
        }
        
        current_table = []
        in_table = False
        table_start_index = -1
        
        for i, line in enumerate(lines):
            # Détection améliorée des tableaux
            if self._is_table_row(line):
                if not in_table:
                    in_table = True
                    current_table = []
                    table_start_index = i
                
                # Nettoyage et séparation des colonnes
                columns = self._split_table_columns(line)
                current_table.append(columns)
                
            else:
                if in_table:
                    # Vérifier si c'est vraiment la fin du tableau
                    if (len(current_table) >= 2 and 
                        (i - table_start_index) > 5 and  # Tableau d'au moins 5 lignes
                        not self._is_possible_table_continuation(line, lines, i)):
                        
                        # Traiter le tableau complet
                        processed_table = self._process_table_data(current_table)
                        if processed_table:
                            data['tables'].append(processed_table)
                        
                        current_table = []
                        in_table = False
                        table_start_index = -1
                
                if line and not in_table:
                    data['raw_data'].append(line)
        
        # Traiter le dernier tableau si on est encore dedans
        if in_table and current_table:
            processed_table = self._process_table_data(current_table)
            if processed_table:
                data['tables'].append(processed_table)
        
        # Extraire les métadonnées
        data['metadata'] = self._extract_tabular_metadata(text)
        
        return data
    
    def _is_table_row(self, line: str) -> bool:
        """Détecte si une ligne fait partie d'un tableau"""
        # Vérifier la présence de séparateurs
        has_separators = re.search(r'\s{2,}|\t|\|', line)
        
        # Vérifier le nombre de "colonnes" (mots séparés)
        words = re.split(r'\s{2,}|\t|\|', line)
        clean_words = [w.strip() for w in words if w.strip()]
        
        # Conditions pour être une ligne de tableau
        return (has_separators and 
                len(clean_words) >= 2 and 
                not re.match(r'^[•\-*\u2022]', line) and  # Pas une puce
                len(line) < 200)  # Pas une ligne trop longue
    
    def _split_table_columns(self, line: str) -> List[str]:
        """Sépare les colonnes d'une ligne de tableau"""
        # Essayer différents séparateurs
        separators = [r'\s{2,}', r'\t', r'\|']
        
        for sep in separators:
            if re.search(sep, line):
                columns = re.split(sep, line)
                # Nettoyer les colonnes
                clean_columns = [col.strip() for col in columns if col.strip()]
                if len(clean_columns) >= 2:
                    return clean_columns
        
        # Fallback: séparation par espace simple
        return [line.strip()]
    
    def _is_possible_table_continuation(self, line: str, all_lines: List[str], current_index: int) -> bool:
        """Détermine si une ligne pourrait être la continuation d'un tableau"""
        if not line.strip():
            return True
        
        # Vérifier les motifs de continuation
        next_lines = all_lines[current_index:current_index + 3]
        table_like_count = sum(1 for l in next_lines if self._is_table_row(l))
        
        return table_like_count >= 2
    
    def _process_table_data(self, table_rows: List[List[str]]) -> Dict[str, Any]:
        """Traite les données brutes d'un tableau pour identifier en-têtes et données"""
        if not table_rows:
            return None
        
        # Identifier les en-têtes (première ligne avec des mots significatifs)
        potential_headers = table_rows[0]
        
        # Vérifier si la première ligne semble être un en-tête
        is_header = all(len(str(cell)) < 50 for cell in potential_headers) and len(potential_headers) >= 2
        
        if is_header and len(table_rows) > 1:
            headers = potential_headers
            rows = table_rows[1:]
        else:
            # Générer des en-têtes automatiques
            headers = [f'Colonne_{i+1}' for i in range(len(table_rows[0]))]
            rows = table_rows
        
        return {
            'headers': headers,
            'rows': rows,
            'row_count': len(rows),
            'column_count': len(headers)
        }
    
    def _extract_tabular_metadata(self, text: str) -> Dict[str, Any]:
        """Extrait les métadonnées spécifiques aux documents tabulaires"""
        metadata = {
            'table_count': text.count('|') // 10,  # Estimation grossière
            'numeric_values': re.findall(r'\b\d{2,}\b', text),  # Nombres à 2+ chiffres
            'percentages': re.findall(r'\d+%', text),
            'dates': re.findall(r'\d{1,2}/\d{1,2}/\d{4}', text)
        }
        return metadata
    
    def _parse_rh_data(self, text: str) -> Dict[str, Any]:
        """Parser spécifique pour les données RH de laboratoire"""
        data = {
            'type': 'rh_laboratoire',
            'personnel_par_grade': [],
            'statistiques': {},
            'observations': [],
            'tableaux': []
        }
        
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Détection des lignes de tableau RH
            if re.search(r'\b(ATMS|TMS|TPMS|ITMS|IMS|ASOL|Agent|Technicien|Ingénieur)\b', line, re.IGNORECASE):
                # Extraire grade et effectif
                grade_match = re.search(r'([A-Za-z\s\(\)]+)\s+(\d+)', line)
                if grade_match:
                    grade = grade_match.group(1).strip()
                    effectif = grade_match.group(2)
                    
                    data['personnel_par_grade'].append({
                        'grade': grade,
                        'effectif': effectif
                    })
            
            # Détection des pourcentages et statistiques
            elif '%' in line or 'pourcent' in line.lower():
                data['observations'].append(line)
            
            # Détection des totaux
            elif 'total' in line.lower() and any(c.isdigit() for c in line):
                data['observations'].append(line)
        
        # Extraire également les tableaux standard
        tabular_data = self._parse_tabular_data_enhanced(text)
        data['tableaux'] = tabular_data.get('tables', [])
        
        # Calculer les totaux
        if data['personnel_par_grade']:
            try:
                total_effectif = sum(int(item['effectif']) for item in data['personnel_par_grade'] if item['effectif'].isdigit())
                data['statistiques']['total_effectif'] = total_effectif
                data['statistiques']['nombre_grades'] = len(data['personnel_par_grade'])
            except ValueError:
                data['statistiques']['total_effectif'] = 'Calcul impossible'
        
        return data

    def _parse_tabular_data(self, text: str) -> Dict[str, Any]:
        """Parse les données tabulaires (version originale)"""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        data = {
            'type': 'tabular',
            'tables': [],
            'raw_data': []
        }
        
        current_table = []
        in_table = False
        
        for line in lines:
            # Détection des lignes tabulaires
            if re.search(r'\s{2,}|\t', line) and len(line.split()) >= 2:
                if not in_table:
                    in_table = True
                    current_table = []
                
                columns = re.split(r'\s{2,}|\t', line.strip())
                current_table.append(columns)
            else:
                if in_table and len(current_table) >= 1:
                    data['tables'].append({
                        'headers': current_table[0] if len(current_table) > 1 else ['Colonne'],
                        'rows': current_table[1:] if len(current_table) > 1 else current_table,
                        'row_count': len(current_table) - 1 if len(current_table) > 1 else len(current_table)
                    })
                    current_table = []
                    in_table = False
                
                if line:
                    data['raw_data'].append(line)
        
        # Ajouter le dernier tableau
        if in_table and current_table:
            data['tables'].append({
                'headers': current_table[0] if len(current_table) > 1 else ['Colonne'],
                'rows': current_table[1:] if len(current_table) > 1 else current_table,
                'row_count': len(current_table) - 1 if len(current_table) > 1 else len(current_table)
            })
        
        return data
    
    def _parse_legal_data(self, text: str) -> Dict[str, Any]:
        """Parse les documents juridiques"""
        data = {
            'type': 'legal',
            'articles': [],
            'sections': [],
            'references': []
        }
        
        lines = text.split('\n')
        current_article = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Détection des articles
            article_match = re.match(r'^Article\s+(\d+)[:\s]*(.*)$', line, re.IGNORECASE)
            if article_match:
                if current_article:
                    data['articles'].append(current_article)
                current_article = {
                    'numero': article_match.group(1),
                    'titre': article_match.group(2).strip(),
                    'contenu': []
                }
                continue
            
            # Détection des sections
            section_match = re.match(r'^§\s*(\d+)[:\s]*(.*)$', line)
            if section_match:
                data['sections'].append({
                    'numero': section_match.group(1),
                    'titre': section_match.group(2).strip()
                })
                continue
            
            # Détection des références légales
            if re.search(r'\b(loi|décret|arrêté|code)\s+n°?\s*\d', line, re.IGNORECASE):
                data['references'].append(line)
                continue
            
            # Ajout au contenu de l'article courant
            if current_article and line:
                current_article['contenu'].append(line)
        
        # Ajouter le dernier article
        if current_article:
            data['articles'].append(current_article)
        
        return data
    
    def _parse_administrative_data(self, text: str) -> Dict[str, Any]:
        """Parse les documents administratifs"""
        data = {
            'type': 'administrative',
            'expediteur': '',
            'destinataire': '',
            'objet': '',
            'reference': '',
            'date': '',
            'contenu': []
        }
        
        lines = text.split('\n')
        in_header = True
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if in_header:
                # Détection de l'expéditeur
                if not data['expediteur'] and any(mot in line.lower() for mot in ['de:', 'expéditeur:', 'from:']):
                    data['expediteur'] = line
                    continue
                
                # Détection du destinataire
                if not data['destinataire'] and any(mot in line.lower() for mot in ['à:', 'destinataire:', 'to:']):
                    data['destinataire'] = line
                    continue
                
                # Détection de l'objet
                if not data['objet'] and any(mot in line.lower() for mot in ['objet:', 'sujet:', 'subject:']):
                    data['objet'] = line
                    continue
                
                # Détection de la référence
                if not data['reference'] and any(mot in line.lower() for mot in ['réf:', 'reference:', 'ref:']):
                    data['reference'] = line
                    continue
                
                # Détection de la date
                if not data['date'] and any(mot in line.lower() for mot in ['date:', 'le:']):
                    data['date'] = line
                    continue
                
                # Fin de l'en-tête quand on trouve du contenu substantiel
                if len(line) > 50 and not any(mot in line.lower() for mot in ['de:', 'à:', 'objet:', 'réf:', 'date:']):
                    in_header = False
            
            if not in_header:
                data['contenu'].append(line)
        
        return data

    def _parse_budget_data(self, text: str) -> Dict[str, Any]:
        """Parse les données de budget d'investissement"""
        data = {
            'type': 'budget',
            'lignes_budgetaires': [],
            'total': 0
        }
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Recherche de montants
            montant_match = re.search(r'(\d{1,3}(?:\s?\d{3})*(?:,\d+)?)\s*€?', line)
            if montant_match:
                ligne_data = {
                    'description': line,
                    'montant': self._parse_montant(montant_match.group(1))
                }
                data['lignes_budgetaires'].append(ligne_data)
                data['total'] += ligne_data['montant']
        
        return data
    
    def _parse_lab_data(self, text: str) -> Dict[str, Any]:
        """Parse les données de laboratoire"""
        data = {
            'type': 'laboratoire',
            'equipements': [],
            'personnel': []
        }
        
        lines = text.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip().lower()
            
            if 'équipement' in line or 'materiel' in line:
                current_section = 'equipements'
            elif 'personnel' in line or 'employé' in line:
                current_section = 'personnel'
            elif line and current_section:
                data[current_section].append(line)
        
        return data
    
    def _parse_voirie_data(self, text: str) -> Dict[str, Any]:
        """Parse les données de voirie"""
        data = {
            'type': 'voirie',
            'troncons': [],
            'infrastructures': []
        }
        
        lines = text.split('\n')
        for line in lines:
            if any(keyword in line.lower() for keyword in ['route', 'rue', 'avenue', 'boulevard']):
                troncon = {'description': line}
                
                # Patterns pour les données de voirie
                longueur_match = re.search(r'longueur[:\s]*(\d+(?:,\d+)?)\s*m', line.lower())
                if longueur_match:
                    troncon['longueur'] = longueur_match.group(1)
                
                largeur_match = re.search(r'largeur[:\s]*(\d+(?:,\d+)?)\s*m', line.lower())
                if largeur_match:
                    troncon['largeur'] = largeur_match.group(1)
                
                type_match = re.search(r'(route|rue|avenue|boulevard|chemin)', line.lower())
                if type_match:
                    troncon['type_voirie'] = type_match.group(1)
                
                data['troncons'].append(troncon)
        
        return data

    # MÉTHODES D'EXTRACTION ET PRÉTRAITEMENT
    def _extract_text(self, filepath: str) -> str:
        """Extrait le texte d'un fichier (PDF ou image) avec améliorations PDF"""
        if filepath.lower().endswith('.pdf'):
            try:
                print("📄 Traitement d'un fichier PDF...")
                
                # Essayer d'abord l'extraction texte directe
                try:
                    import PyPDF2
                    with open(filepath, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in pdf_reader.pages:
                            text += page.extract_text() + "\n"
                        
                        # Si l'extraction directe donne du texte valide, l'utiliser
                        if len(text.strip()) > 50:
                            print("✅ Texte extrait directement du PDF")
                            return text
                except Exception as e:
                    print(f"⚠️ Extraction PDF directe échouée: {e}")
                
                # Fallback: conversion image + OCR
                print("🔄 Conversion PDF en images pour OCR...")
                images = pdf2image.convert_from_path(filepath, dpi=300)  # Augmenter la résolution
                text = ""
                for i, image in enumerate(images):
                    print(f"📄 Traitement page {i+1}/{len(images)}")
                    page_text = self._extract_text_from_image(image)
                    text += f"--- Page {i+1} ---\n{page_text}\n\n"
                
                return text
                
            except Exception as e:
                print(f"❌ Erreur conversion PDF: {e}")
                return ""
        else:
            return self._extract_text_from_image(filepath)
    
    def _extract_text_from_image(self, image_path) -> str:
        """Extrait le texte d'une image avec prétraitement amélioré"""
        try:
            # Charger l'image
            if isinstance(image_path, str):
                image = cv2.imread(image_path)
                if image is None:
                    return "Erreur: Impossible de charger l'image"
            else:
                image = cv2.cvtColor(np.array(image_path), cv2.COLOR_RGB2BGR)
            
            print(f"📐 Dimensions image: {image.shape}")
            
            # Redimensionner si trop petite (au moins 300px de hauteur)
            height, width = image.shape[:2]
            if height < 300:
                scale_factor = 300 / height
                new_width = int(width * scale_factor)
                image = cv2.resize(image, (new_width, 300), interpolation=cv2.INTER_CUBIC)
                print(f"🔄 Image redimensionnée: {image.shape}")
            
            # Prétraitement amélioré
            processed_image = self._preprocess_image_enhanced(image)
            
            # Configurations Tesseract à essayer
            configs = [
                '--oem 3 --psm 6 -l fra+eng',  # Par défaut
                '--oem 3 --psm 3 -l fra+eng',  # Page entière sans segmentation
                '--oem 3 --psm 4 -l fra+eng',  # Colonne unique de texte
                '--oem 3 --psm 8 -l fra+eng',  # Mot unique
                '--oem 3 --psm 11 -l fra+eng', # Sparse text
            ]
            
            best_text = ""
            best_config = ""
            
            for config in configs:
                try:
                    text = pytesseract.image_to_string(processed_image, config=config)
                    print(f"🔍 Config {config}: {len(text.strip())} caractères")
                    
                    if len(text.strip()) > len(best_text.strip()):
                        best_text = text
                        best_config = config
                except Exception as e:
                    print(f"⚠️ Erreur config {config}: {e}")
                    continue
            
            print(f"✅ Meilleure config: {best_config}")
            print(f"✅ Texte extrait: {len(best_text)} caractères")
            
            if best_text.strip():
                return best_text
            else:
                # Essayer avec l'image originale en dernier recours
                try:
                    fallback_text = pytesseract.image_to_string(image, config='--oem 3 --psm 6 -l fra+eng')
                    print(f"🔄 Fallback texte: {len(fallback_text.strip())} caractères")
                    return fallback_text
                except:
                    return "Aucun texte détecté dans l'image"
                
        except Exception as e:
            print(f"❌ Erreur extraction OCR: {e}")
            return f"Erreur lors de l'extraction OCR: {e}"
    
    def _preprocess_image_enhanced(self, image):
        """Améliore la qualité de l'image pour l'OCR avec plusieurs techniques"""
        try:
            # Convertir en niveaux de gris
            if len(image.shape) == 3:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            else:
                gray = image
            
            # Dénoniser l'image
            denoised = cv2.medianBlur(gray, 3)
            
            # Plusieurs techniques de seuillage
            # 1. Seuillage adaptatif gaussien
            thresh1 = cv2.adaptiveThreshold(
                denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 11, 2
            )
            
            # 2. Seuillage d'Otsu
            _, thresh2 = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # 3. Amélioration du contraste
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            contrast_enhanced = clahe.apply(denoised)
            _, thresh3 = cv2.threshold(contrast_enhanced, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Essayer les différentes versions et choisir la meilleure
            images_to_try = [thresh1, thresh2, thresh3, denoised]
            
            # Tester rapidement chaque version
            best_image = thresh1
            best_text_length = 0
            
            for img in images_to_try:
                try:
                    text = pytesseract.image_to_string(img, config='--oem 3 --psm 6 -l fra+eng')
                    if len(text.strip()) > best_text_length:
                        best_text_length = len(text.strip())
                        best_image = img
                except:
                    continue
            
            print(f"✅ Texte détecté: {best_text_length} caractères")
            return best_image
            
        except Exception as e:
            print(f"❌ Erreur prétraitement image: {e}")
            return image

    def _preprocess_image(self, image):
        """Ancienne méthode de prétraitement (conservée pour compatibilité)"""
        return self._preprocess_image_enhanced(image)
    
    def _parse_montant(self, montant_str: str) -> float:
        """Convertit une chaîne de montant en float"""
        try:
            clean = montant_str.replace(' ', '').replace(',', '.')
            return float(clean)
        except:
            return 0.0

    # MÉTHODES UNIVERSELES (nécessaires pour _parse_universal)
    def _extract_metadata(self, text: str) -> Dict[str, Any]:
        """Extrait les métadonnées du document"""
        metadata = {
            'dates': re.findall(r'\d{1,2}/\d{1,2}/\d{4}|\d{1,2}\s+\w+\s+\d{4}', text),
            'amounts': re.findall(r'\d{1,3}(?:[ \.]\d{3})*(?:,\d+)?\s*€?', text),
            'emails': re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text),
            'urls': re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text),
        }
        return metadata
    
    def _analyze_document_structure(self, lines: List[str]) -> Dict[str, Any]:
        """Analyse la structure hiérarchique du document"""
        structure = {
            'title_levels': [],
            'paragraphs': [],
            'lists': [],
            'headings': []
        }
        
        for i, line in enumerate(lines):
            # Détection des titres
            if self._is_title(line, i, lines):
                level = self._determine_title_level(line)
                structure['title_levels'].append({
                    'text': line,
                    'level': level,
                    'position': i
                })
            
            # Détection des listes
            elif self._is_list_item(line):
                structure['lists'].append({
                    'text': line,
                    'position': i,
                    'type': 'ordered' if re.match(r'^\d+\.', line) else 'unordered'
                })
            
            # Paragraphes normaux
            elif len(line) > 20:
                structure['paragraphs'].append({
                    'text': line,
                    'position': i,
                    'length': len(line)
                })
        
        return structure
    
    def _is_title(self, line: str, index: int, all_lines: List[str]) -> bool:
        """Détermine si une ligne est un titre"""
        if len(line) > 150:
            return False
        
        # Titres en majuscules
        if line.isupper() and len(line) > 5:
            return True
        
        # Titres avec formatage spécifique
        title_patterns = [
            r'^[IVX]+\.',  # Chiffres romains
            r'^\d+\.',     # Chiffres arabes
            r'^[A-Z]\.',   # Lettres majuscules
            r'^§',         # Paragraphe
            r'^Article',   # Article
        ]
        
        return any(re.match(pattern, line.strip()) for pattern in title_patterns)
    
    def _determine_title_level(self, line: str) -> int:
        """Détermine le niveau hiérarchique d'un titre"""
        if line.isupper():
            return 1
        elif re.match(r'^[IVX]+\.', line):
            return 2
        elif re.match(r'^\d+\.', line):
            return 3
        elif re.match(r'^[a-z]\.', line):
            return 4
        else:
            return 5
    
    def _is_list_item(self, line: str) -> bool:
        """Détermine si une ligne est un élément de liste"""
        list_patterns = [
            r'^[•\-*\u2022]',  # Puces
            r'^\d+\.',         # Numérotation
            r'^[a-z]\)',       # Lettres minuscules
        ]
        return any(re.match(pattern, line.strip()) for pattern in list_patterns)
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extrait les entités nommées basiques"""
        entities = {
            'organizations': [],
            'locations': [],
            'dates': [],
            'amounts': []
        }
        
        # Organisations (mots en majuscules de plus de 2 caractères)
        organizations = re.findall(r'\b[A-Z][A-Z&]+\b', text)
        entities['organizations'] = list(set(org for org in organizations if len(org) > 2))
        
        # Localisations (mots avec capitale)
        locations = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', text)
        entities['locations'] = list(set(loc for loc in locations if len(loc.split()) <= 3))
        
        return entities
    
    def _extract_semantic_sections(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extrait les sections sémantiques du document"""
        sections = []
        current_section = []
        current_title = "Introduction"
        
        for line in lines:
            if self._is_title(line, 0, lines):  # Nouvelle section
                if current_section:
                    sections.append({
                        'title': current_title,
                        'content': current_section,
                        'word_count': sum(len(text.split()) for text in current_section)
                    })
                current_section = []
                current_title = line
            else:
                current_section.append(line)
        
        # Ajouter la dernière section
        if current_section:
            sections.append({
                'title': current_title,
                'content': current_section,
                'word_count': sum(len(text.split()) for text in current_section)
            })
        
        return sections
    
    def _extract_tabular_data(self, lines: List[str]) -> List[Dict[str, Any]]:
        """Extrait les données tabulaires"""
        tables = []
        current_table = []
        
        for line in lines:
            # Détection des lignes tabulaires (au moins 3 colonnes)
            if re.search(r'\s{2,}|\t', line) and len(line.split()) >= 3:
                columns = re.split(r'\s{2,}|\t', line.strip())
                current_table.append(columns)
            elif current_table:
                # Fin d'un tableau
                if len(current_table) >= 2:  # Au moins un en-tête et une ligne de données
                    tables.append({
                        'headers': current_table[0],
                        'rows': current_table[1:],
                        'row_count': len(current_table) - 1
                    })
                current_table = []
        
        return tables