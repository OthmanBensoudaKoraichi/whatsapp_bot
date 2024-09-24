import streamlit as st
from ppadb.client import Client as AdbClient
import subprocess
import time
import pandas as pd
import os

# Variable de contrôle pour stopper le processus
st.session_state["stop"] = False


# Démarrer le serveur ADB
def start_adb_server():
    subprocess.run(["adb", "start-server"])


# Fonction pour stopper le processus
def stop_process():
    st.session_state["stop"] = True


# Fonction pour envoyer des messages WhatsApp via ADB avec la possibilité d'ajouter un fichier
def send_whatsapp_message(device, phone_number_list, message, x_coord, y_coord, file_path=None):
    encoded_message = message.replace(" ", "%20")

    for phone_number in phone_number_list:
        if st.session_state["stop"]:
            st.write("Processus arrêté.")
            break

        # Commande pour ouvrir WhatsApp avec le message et le numéro
        open_whatsapp_command = f'am start -a android.intent.action.VIEW -d "https://api.whatsapp.com/send?phone={phone_number}&text={encoded_message}"'
        device.shell(open_whatsapp_command)

        # Attendre l'ouverture de WhatsApp
        time.sleep(5)

        # Ajouter une pièce jointe si spécifiée
        if file_path:
            st.write(f"Envoi du fichier à {phone_number}...")
            # Ouvrir la galerie pour sélectionner le fichier
            device.shell('am start -a android.intent.action.VIEW -t image/*')
            time.sleep(3)
            # Simuler le clic pour envoyer le fichier
            device.shell(f'input tap {x_coord} {y_coord}')
            time.sleep(2)

        # Commande ADB pour taper sur le bouton d'envoi
        device.shell(f'input tap {x_coord} {y_coord}')

        # Attendre avant d'envoyer le message suivant
        time.sleep(1)

        st.write(f"Message envoyé à {phone_number}")


# Interface Streamlit
st.title("WhatsApp Bot")

# Démarrer le serveur ADB
if st.button("Démarrer le serveur ADB"):
    start_adb_server()
    st.write("Serveur ADB démarré !")

# Connexion au serveur ADB
client = AdbClient(host="127.0.0.1", port=5037)
devices = client.devices()

# Vérifier si un appareil est connecté
if len(devices) == 0:
    st.write("Aucun appareil connecté. Veuillez connecter un appareil.")
else:
    device = devices[0]
    st.write(f"Appareil connecté : {device}")

    # Importer un fichier Excel contenant les numéros de téléphone (dans la troisième colonne)
    uploaded_file = st.file_uploader("Charger un fichier Excel avec les numéros de téléphone", type=["xlsx"])
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        phone_number_list = df.iloc[:, 2].tolist()  # Supposant que les numéros sont dans la 3ème colonne
        st.write(f"{len(phone_number_list)} numéros de téléphone chargés.")

    # Entrer le message et télécharger un fichier optionnel
    message = st.text_area("Message à envoyer", "Bonjour !")
    file = st.file_uploader("Ajouter une photo ou un fichier (optionnel)")

    # Obtenir le chemin du fichier téléchargé
    if file is not None:
        with open(os.path.join("tempDir", file.name), "wb") as f:
            f.write(file.getbuffer())
        file_path = os.path.join("tempDir", file.name)
        st.write(f"Fichier {file.name} chargé.")
    else:
        file_path = None

    # Coordonnées pour taper sur le bouton d'envoi
    x_coord = 1000
    y_coord = 2000

    # Boutons pour démarrer et stopper l'envoi
    if st.button("Envoyer les messages"):
        st.session_state["stop"] = False
        send_whatsapp_message(device, phone_number_list, message, x_coord, y_coord, file_path)

    if st.button("Stopper l'envoi"):
        stop_process()
        st.write("L'envoi a été interrompu.")
