import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.metrics import classification_report, accuracy_score

# Load dataset
df = pd.read_csv('spam_ham_dataset.csv')

# If the actual text column is not named 'text', rename accordingly
if 'text' not in df.columns:
    # try to guess the correct column
    text_column = [col for col in df.columns if 'text' in col.lower()]
    if text_column:
        df.rename(columns={text_column[0]: 'text'}, inplace=True)

# If the label column is not exactly 'label', fix it
if 'label' not in df.columns:
    label_column = [col for col in df.columns if 'label' in col.lower()]
    if label_column:
        df.rename(columns={label_column[0]: 'label'}, inplace=True)

# Encode label (ham = 0, spam = 1)
df['label'] = df['label'].map({'ham': 0, 'spam': 1})

# Drop any rows with missing values in text or label
df.dropna(subset=['text', 'label'], inplace=True)

# Split dataset
X_train, X_test, y_train, y_test = train_test_split(
    df['text'], df['label'], test_size=0.2, random_state=42, stratify=df['label']
)

# Vectorize text using TF-IDF
vectorizer = TfidfVectorizer(stop_words='english')
X_train_vec = vectorizer.fit_transform(X_train)
X_test_vec = vectorizer.transform(X_test)

# Train model
model = MultinomialNB()
model.fit(X_train_vec, y_train)

# Predict and evaluate
y_pred = model.predict(X_test_vec)
print("Accuracy:", accuracy_score(y_test, y_pred))
print("Classification Report:\n", classification_report(y_test, y_pred))

# Save model and vectorizer
import joblib
joblib.dump(model, 'spam_detector_model.pkl')
joblib.dump(vectorizer, 'tfidf_vectorizer.pkl')
