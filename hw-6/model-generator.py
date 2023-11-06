import pandas as pd
import re
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OrdinalEncoder
from sklearn.metrics import accuracy_score
import joblib
import sqlalchemy
from google.cloud.sql.connector import Connector, IPTypes
import pymysql

# Import the Secret Manager client library.
from google.cloud import secretmanager

# GCP project in which to store secrets in Secret Manager.
project_id = "ds-561-am"

# ID of the secret to create.
secret_ids = ["db_user","db_pass","db_name","sql_INSTANCE_CONNECTION_NAME","pub_ip"]

creds = {}

def access_secret_version(secret_id, version_id="latest"):
    # Create the Secret Manager client.
    client = secretmanager.SecretManagerServiceClient()

    # Build the resource name of the secret version.
    name = f"projects/{project_id}/secrets/{secret_id}/versions/{version_id}"

    # Access the secret version.
    response = client.access_secret_version(name=name)

    # Return the decoded payload.
    return response.payload.data.decode('UTF-8')

for secret_id in secret_ids:
    # Access the secret version.
    
    creds[secret_id] = access_secret_version(secret_id=secret_id)

def connect_with_connector() -> sqlalchemy.engine.base.Engine:
    """
    Initializes a connection pool for a Cloud SQL instance of MySQL.

    Uses the Cloud SQL Python Connector package.
    """

    global creds

    instance_connection_name = creds["sql_INSTANCE_CONNECTION_NAME"]  # e.g. 'project:region:instance'
    db_user = creds["db_user"]  # e.g. 'my-db-user'
    db_pass = creds["db_pass"]  # e.g. 'my-db-password'
    db_name = creds["db_name"]  # e.g. 'my-database'

    ip_type = IPTypes.PUBLIC

    connector = Connector(ip_type)

    def getconn() -> pymysql.connections.Connection:
        conn: pymysql.connections.Connection = connector.connect(
            instance_connection_name,
            "pymysql",
            user=db_user,
            password=db_pass,
            db=db_name,
        )
        return conn

    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=getconn,
        pool_size=5,
        max_overflow=2,
        pool_timeout=30,
        pool_recycle=1800, 
    )
    return pool




def init_connection_pool() -> sqlalchemy.engine.base.Engine:
    """Sets up connection pool for the app."""
    return connect_with_connector()


# create 'votes' table in database if it does not already exist
def migrate_db(db: sqlalchemy.engine.base.Engine) -> None:
    """Creates the `users`, `requests`, `failed-requests` tables if it doesn't exist."""
    with db.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                    "CREATE TABLE IF NOT EXISTS Users (user_id INT AUTO_INCREMENT PRIMARY KEY, client_ip VARCHAR(15), gender VARCHAR(10), age INT, income FLOAT, is_banned BOOLEAN);"
            )
        )

        conn.execute(
            sqlalchemy.text(
                    "CREATE TABLE IF NOT EXISTS Requests (request_id INT AUTO_INCREMENT PRIMARY KEY, user_id INT, country VARCHAR(50), time_of_day TIME, requested_file VARCHAR(255),FOREIGN KEY(user_id) REFERENCES Users(user_id));"
            )
        )

        conn.execute(
            sqlalchemy.text(
                     "CREATE TABLE IF NOT EXISTS FailedRequests (request_id INT AUTO_INCREMENT PRIMARY KEY, time_of_request TIMESTAMP, requested_file VARCHAR(255), error_code INT);"
            )
        )

        
        conn.commit()


db = None


def init_db() -> sqlalchemy.engine.base.Engine:
    """Initiates connection to database and its' structure."""
    global db
    db = init_connection_pool()
    migrate_db(db)

def get_users():
    global db

    db = init_connection_pool()

    # Define the SQL query
    sql_query = sqlalchemy.text("SELECT * FROM Users")

    # Use the connection as a context manager to ensure it's closed after use
    with db.connect() as conn:
        # Execute the query and return a DataFrame
        users_df = pd.read_sql(sql_query, conn)
        return users_df
    

def get_requests():
    global db

    db = init_connection_pool()

    # Define the SQL query
    sql_query = sqlalchemy.text("SELECT * FROM Requests")

    # Use the connection as a context manager to ensure it's closed after use
    with db.connect() as conn:
        # Execute the query and return a DataFrame
        requests_df = pd.read_sql(sql_query, conn)
        return requests_df


# Load the Users data
users_df = get_users()
requests_df = get_requests()

merged_df = pd.merge(requests_df, users_df, on='user_id')

print(merged_df.columns)

# Function to validate IP addresses
def is_valid_ip(ip_addr):
    if not isinstance(ip_addr, str) or ip_addr.lower() == 'n.n':
        return False
    pattern = re.compile(r"^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$")
    if pattern.match(ip_addr):
        return all(0 <= int(num) < 256 for num in ip_addr.rstrip().split('.'))
    else:
        return False


# Apply the function to filter out invalid IPs
merged_df['is_valid'] = merged_df['client_ip'].apply(is_valid_ip)

merged_df = merged_df[~merged_df['client_ip'].str.contains('N,N', na=False)]

merged_df = merged_df.dropna()
merged_df_new = merged_df

# Code for Model 2 predicting income and pickling it

# Define the order of categories for ordinal encoding
age_categories = ['0-16', '17-25', '26-35', '36-45', '46-55', '56-65', '66-75', '76+']
income_categories = ['0-10k', '10k-20k', '20k-40k', '40k-60k', '60k-100k', '100k-150k', '150k-250k', '250k+']

# Fit the encoder for 'age'
age_encoder = OrdinalEncoder(categories=[age_categories])
merged_df_new['age'] = age_encoder.fit_transform(merged_df_new[['age']])

# Fit the encoder for 'income'
income_encoder = OrdinalEncoder(categories=[income_categories])
merged_df_new['income'] = income_encoder.fit_transform(merged_df_new[['income']])


# Select features and target
X = merged_df_new.drop(['income'], axis=1)
y = merged_df_new['income'].astype(int)


# Split into train and test sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

categorical_features = ['client_ip', 'gender', 'is_banned', 'country', 'requested_file']
numerical_features = ['user_id', 'age']  # 'age' is now numerical after ordinal encoding

# Define transformers
categorical_transformer = Pipeline(steps=[
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
    ('onehot', OneHotEncoder(handle_unknown='ignore'))])

# We do not need a numerical_transformer since 'age' is already encoded and 'user_id' may not need scaling or imputation

# Combine preprocessing steps
preprocessor = ColumnTransformer(
    transformers=[
        ('cat', categorical_transformer, categorical_features)])

# Create the Random Forest classifier pipeline
model = Pipeline(steps=[('preprocessor', preprocessor),
                        ('classifier', RandomForestClassifier(random_state=42))])

# Train the model
model.fit(X_train, y_train)

# Predict on the test set
y_pred = model.predict(X_test)

print(y_pred)

# Calculate accuracy
accuracy = accuracy_score(y_test, y_pred)

# Print the accuracy
print(f"Model Income Accuracy: {accuracy * 100:.2f}%")

joblib.dump(age_encoder, 'age_encoder.pkl')
joblib.dump(income_encoder, 'income_encoder.pkl')


# Save the model
joblib.dump(model, 'model_income.pkl')


# Code for Model 1 predicting country and pickling it

# Let's convert IP addresses to a numerical format for training
def ip_to_int(ip):
    octets = ip.split('.')
    base = 256
    ip_int = sum([int(octets[i]) * (base ** (3 - i)) for i in range(4)])
    return ip_int

merged_df['ip_int'] = merged_df['client_ip'].apply(ip_to_int)

# Now, let's prepare our data for training
X = merged_df[['ip_int']]  # Features
y = merged_df['country']   # Labels

# Split the data into training and testing sets
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create a Random Forest Classifier
clf = RandomForestClassifier(n_estimators=100, random_state=42)

# Train the classifier
clf.fit(X_train, y_train)

# Predict on the test set
y_pred = clf.predict(X_test)

# Evaluate the model
accuracy = accuracy_score(y_test, y_pred)
print(f'Model Country accuracy: {accuracy * 100:.2f}%')

joblib.dump(clf, 'model_country.pkl')