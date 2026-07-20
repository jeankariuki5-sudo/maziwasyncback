import json
import os

from groq import Groq
import joblib
from dotenv import load_dotenv



class CattleAIService:
    def __init__(self):
        # constructor that will load the ML files and initialize the Grok AI engine
        base_dir = os.path.dirname(__file__)

        # reads keys inside the local.env
        load_dotenv()
        self.model = joblib.load(os.path.join(base_dir, 'cattle_diseases_model.pkl'))

        # loading the features/x/inputs
        self.model_features = joblib.load(os.path.join(base_dir, 'model_features.pkl'))

        # extract the symptoms from te model features
        self.valid_symptoms = [
            f for f in self.model_features
            if f not in ['Age', 'Temperature'] and not f.startswith('Animal')
        ]

        # Setup and authenticate the groq connection
        self.groq_client = Groq(api_key = os.environ.get('GROQ_API_KEY'))

    # Method to extract the farmer covo structure symptoms
    def extract_symptoms_with_grok(self, farmer_text):
        # Command grok and force it to respond strictly with valid symptoms in json format
        system_prompt = f"""
            You are a vetenary assistant. Analyse the text and extract symptoms matching exactly this list
            {self.valid_symptoms}
            Respond with a JSON object{{"Symptoms" : ["symptom_name"]}}
        """
        
        try:
            # request processing from LLM model using structured json output
            completion = self.groq_client.chat.completions.create(
                messages = [
                    {"role" : "system", "content" :system_prompt},
                    {"role": "user", "content" : f"Farmer text: \"{farmer_text}\""}
                ],
                model = "llama-3.1-8b-instant",
                temperature=0.0,
                response_format={"type" : "json_object"}
            )
            response_text = completion.choices[0].message.content.strip()
            result_json = json.loads(response_text)
            return result_json.get("Symptoms" , [])

        except Exception as e:
            print(f"Groq Extraction error", (e))

    def get_treatement_reccomendation(self, disease, animal_type):
        # Query the groq LLM to generate an instant medical advice and emergency instruction
        system_prompt = ("""
            You are an expert in livestock veterinarian. Provide clear, concise and proffessional treatement recommendations under 120 words using short bullet points. include a vet disclaimer.
        """)
        try:
            completion = self.groq_client.chat.completions.create(
                messages = [
                    {"role" : "system", "content" :system_prompt},
                    {"role": "user", "content" : f"Treatement recommendation for {animal_type} with {disease}"}
                ],
                model = "llama-3.1-8b-instant",
                temperature=0.3 # Higher vaue allows the AI to sound more natural.
            )
            return completion.choices[0].message.content.strip()
        
        except Exception as e:
            print(f"Groq treatment Error{e}")
            return "Treatement temporarily unavailable"

    # Predict method
    def predict(self, animal_type, age, temp, description):
        # Use the LLM extraction utility to filter symptoms out of the incoming text string
        extracted_symptoms = self.extract_symptoms_with_grok(description)

        # Build baseline dictionary mapping all training feautures name to zero values
        input_data = {feature:0 for feature in self.model_features}

        # Map raw numeric inputs to their respective matching feature keys
        input_data['Age'] = age
        input_data['Temperature'] = temp

        # Convert animal string into one columns key format name string 'Animal_cow'
        animal_key = f"Animal_{str(animal_type).strip().lower()}"
        if animal_key in input_data:
            input_data[animal_key] = 1

        for Symptom in extracted_symptoms:
            if Symptom in input_data:
                input_data[Symptom]  = 1

        # flatten the dict into ordered list matching the exact index setup for our model expects
        final_input_vector = [input_data[feature] for feature in self.model_features]

        # predict using our model providing it with the ordered feature/x/input
        prediction = self.model.predict([final_input_vector])

        # Extract the prediction at index 0
        predicted_disease = prediction[0]

        treatement_plan = self.get_treatement_reccomendation(predicted_disease, animal_type)

        # Return consolidated final pipeline payload output directly back to DRF response
        return{
            "status" : "success",
            "extracted_symptoms_by_ai" : extracted_symptoms,
            "predicted_disease" : predicted_disease,
            "treatement_recommendation" : treatement_plan
        }