from flask import Flask, request, jsonify
import joblib
import pandas as pd

app = Flask(__name__)

# Load the model and the encoder
model = joblib.load('model_income.pkl')
age_encoder = joblib.load('age_encoder.pkl')
income_encoder = joblib.load('income_encoder.pkl')

@app.route('/predict', methods=['POST'])
def predict():
    print('hello')
    data = request.get_json()

    # Assuming the data is in the form of a dictionary with keys matching the feature names
    # We convert it to a DataFrame
    df = pd.DataFrame([data])

    # Preprocess the data
    processed_df = preprocess(df)

    print(processed_df)

    # Make prediction
    prediction = model.predict(processed_df)

    # Reverse the ordinal encoding to get the original income category
    prediction_category = reverse_encode(prediction)

    return jsonify({'predicted_income_range': prediction_category})

def preprocess(df):
    # Apply the ordinal encoding to age
    # Note: If the 'age' field is not present, add error handling
    df['age'] = age_encoder.transform(df[['age']])

    # Since the model's pipeline takes care of other preprocessing,
    # we only need to apply the encoder and ensure the data structure matches
    return df

def reverse_encode(prediction):
    # Use the encoder to reverse the predicted labels back to original categories
    print(income_encoder)
    income_categories = income_encoder.categories_[0]  # Assuming income categories are the second field in the encoder
    print(prediction)
    prediction_category = [income_categories[int(label)] for label in prediction]
    return prediction_category

if __name__ == '__main__':
    app.run(debug=True)
