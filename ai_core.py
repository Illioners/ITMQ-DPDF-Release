import os
import json
import re

class ModelManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            
            # Identify path (Portable Mode)
            import sys
            if getattr(sys, 'frozen', False):
                # If compiled, look next to the .exe
                base_dir = os.path.dirname(sys.executable)
            else:
                # If script, look in the script's folder
                base_dir = os.path.dirname(os.path.abspath(__file__))
                
            cls._instance.kb_path = os.path.join(base_dir, "data", "training_data.json")
            cls._instance.data = []
            cls._instance.model = None
            cls._instance.vectorizer = None
            cls._instance.single_class_mode = None
            cls._instance._prediction_cache = {}
            cls._instance._load_data()
            try:
                cls._instance.train() # Train on startup if data exists
            except:
                pass
        return cls._instance
    
    def _load_data(self):
        if os.path.exists(self.kb_path):
            try:
                with open(self.kb_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except:
                self.data = []
    
    def _save_data(self):
        with open(self.kb_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False)
            
    def learn(self, text, category):
        """Add sample and retrain"""
        clean_text = self._clean(text)
        if not clean_text or len(clean_text) < 10:
            return
            
        self.data.append({"text": clean_text, "category": category})
        self._prediction_cache.clear() # Cache invalidation on new data
        self._save_data()
        self.train()
        
    def train(self):
        if not self.data:
            return
            
        try:
            from sklearn.feature_extraction.text import CountVectorizer
            from sklearn.feature_extraction.text import TfidfTransformer
            from sklearn.naive_bayes import MultinomialNB
            from sklearn.pipeline import Pipeline
            
            texts = [d['text'] for d in self.data]
            labels = [d['category'] for d in self.data]
            
            if len(set(labels)) < 2:
                # Special case: Only 1 class learned so far.
                # We can't train a classifier, but we can predict this single class.
                self.single_class_mode = list(set(labels))[0]
                self.model = None
                print(f"Single class mode: {self.single_class_mode}")
                return True
            else:
                self.single_class_mode = None
            
            self.model = Pipeline([
                ('vect', CountVectorizer(stop_words=None)),
                ('tfidf', TfidfTransformer()),
                ('clf', MultinomialNB()),
            ])
            
            self.model.fit(texts, labels)
            self._prediction_cache.clear()
            print(f"Model trained on {len(texts)} samples.")
            return True
            
        except Exception as e:
            print(f"Training failed: {e}")
            return False
            
    def predict(self, text):
        if not text: return None
        
        # Handle Single Class Mode (Training not possible but prediction is fixed)
        if self.single_class_mode:
            return self.single_class_mode
            
        if not self.model:
            return None
            
        if text in self._prediction_cache:
            return self._prediction_cache[text]
            
        try:
            clean = self._clean(text)
            if not clean: return None
            
            # Use predict_proba for confidence
            probs = self.model.predict_proba([clean])[0]
            max_prob = max(probs)
            
            # Threshold (0.35 is a conservative start for NB)
            if max_prob < 0.35:
                # Prediction is too weak
                self._prediction_cache[text] = None
                return None
                
            index = list(probs).index(max_prob)
            result = self.model.classes_[index]
            self._prediction_cache[text] = result
            return result
        except:
            return None
            
    def get_stats(self):
        """Return stats for UI"""
        total = len(self.data)
        cats = {}
        for d in self.data:
            c = d['category']
            cats[c] = cats.get(c, 0) + 1
        return total, cats

    _clean_regex = re.compile(r'[^a-záéíóúñ0-9\s]')
    
    def _clean(self, text):
        if not text: return ""
        text = str(text).lower()
        # Keep basic Latin + Numbers (Using pre-compiled regex)
        text = self._clean_regex.sub(' ', text)
        return " ".join(text.split())
