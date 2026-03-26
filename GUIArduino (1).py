import customtkinter as ctk
import serial
import serial.tools.list_ports
import threading
import time

# --- 1. Variables Globales ---
arduino = None
is_acquiring = False
latest_reading = "0.0"

anciennes_valeurs_pid = {
    "KpPos": None,
    "KiPos": None,
    "KdPos": None,
    "KpCour": None,
    "KiCour": None
}

# --- 2. Logique de Connexion ---
def get_available_ports():
    ports = serial.tools.list_ports.comports()
    port_list = [port.device for port in ports]
    return port_list if port_list else ["Aucun port"]

def connect_serial():
    global arduino
    selected_port = port_combobox.get()
    selected_baud = int(baudrate_combobox.get())
    
    if selected_port == "Aucun port":
        status_label.configure(text="Erreur: Aucun port trouvé", text_color="#e74c3c")
        return

    if arduino and arduino.is_open:
        arduino.close()

    try:
        arduino = serial.Serial(selected_port, selected_baud, timeout=1)
        status_label.configure(text=f"Connecté: {selected_port} à {selected_baud}", text_color="#3498db")
    except serial.SerialException:
        status_label.configure(text=f"Erreur: Impossible d'ouvrir {selected_port}", text_color="#e74c3c")
        arduino = None

# --- 3. Thread de Lecture ---
# --- 3. Thread de Lecture ---
def read_serial_data():
    global is_acquiring
    while is_acquiring and arduino and arduino.is_open:
        try:
            # On englobe in_waiting DANS le try pour intercepter la déconnexion
            if arduino.in_waiting > 0:
                raw_data = arduino.readline().decode('utf-8').strip()
                if raw_data:
                    app.after(0, update_data_display, raw_data)
            
            # Pause de 10 millisecondes (VITAL pour laisser respirer le CPU)
            time.sleep(0.01) 

        except serial.SerialException:
            # Cette exception attrape l'erreur "Handle is invalid" proprement
            print("Connexion série interrompue ou port fermé.")
            is_acquiring = False
            break
        except Exception as e:
            print(f"Erreur de lecture inattendue : {e}")
            time.sleep(0.1) # Petite pause en cas d'erreur de décodage pour ne pas spammer la console

def update_data_display(data):
    global latest_reading
    latest_reading = data
    
    try:
        # On essaie de convertir en float
        valeur_numerique = float(data)
        data_label.configure(text=f"{valeur_numerique:.1f} g")
    except ValueError:
        # Si c'est du texte (comme une erreur de l'Arduino), on l'affiche dans la console
        # ou on l'ignore sans faire planter le GUI
        print(f"Message de l'Arduino (non-numérique) : {data}")

# --- 4. Commandes ---
def start_acquisition():
    global is_acquiring
    if not arduino or not arduino.is_open:
        status_label.configure(text="Erreur: Non connecté", text_color="#e74c3c")
        return

    if not is_acquiring:
        is_acquiring = True 
        threading.Thread(target=read_serial_data, daemon=True).start()
        status_label.configure(text="Status: Acquisition en cours", text_color="#2ecc71")
        app.after(1000, executer_cal_et_tare)

def executer_cal_et_tare():
    if is_acquiring and arduino and arduino.is_open:
        Cal(0)
        # On peut même rajouter un petit délai entre le Cal et le Tare si l'Arduino en a besoin
        app.after(1000, tare)

def tare():
    global latest_reading
    if arduino and arduino.is_open:
        arduino.write(f"Tare:{latest_reading}\n".encode('utf-8'))
        status_label.configure(text="Status: Tare effectuée", text_color="#2ecc71")
    else:
        status_label.configure(text="Erreur: Non connecté", text_color="#e74c3c")

# --- 5. Changement de Mode (NOUVEAU) ---
def change_mode(choice):
    """Bascule entre l'affichage Normal et l'affichage Setup."""
    if choice == "Mode Normal":
        # Cacher le setup, afficher le normal
        setup_frame.pack_forget()
        Cal_frame.pack_forget()
        normal_frame.pack(fill="both", expand=True, pady=10)
    elif choice == "Mode Setup":
        # Cacher le normal, afficher le setup
        normal_frame.pack_forget()
        Cal_frame.pack_forget()
        setup_frame.pack(fill="both", expand=True, pady=10)
    elif choice == "Mode Calibration":
        # Cacher le normal, afficher le setup
        normal_frame.pack_forget()
        setup_frame.pack_forget()
        Cal_frame.pack(fill="both", expand=True, pady=10)

def save_setup():
    """Exemple de fonction pour le mode Setup"""
    cal_value = cal_entry.get()
    print(f"Sauvegarde de la calibration: {cal_value}")
    # Vous pourriez envoyer ça à l'Arduino ici : arduino.write(f"CAL:{cal_value}\n".encode('utf-8'))

def SetPID():
    """Exemple de fonction pour le mode Setup"""
    global anciennes_valeurs_pid # Permet de modifier le dictionnaire mémoire
    
    # 1. On lit les valeurs actuelles des cases (avec les bons noms d'entry)
    nouvelles_valeurs = {
        "KpPos": KpPos_entry.get(),
        "KiPos": KiPos_entry.get(),
        "KdPos": KdPos_entry.get(),
        "KpCour": KpCour_entry.get(),
        "KiCour": KiCour_entry.get()
    }
    
    # 2. On compare chaque nouvelle valeur avec l'ancienne
    for parametre, valeur_lue in nouvelles_valeurs.items():
        
        # On s'assure que la case n'est pas vide pour éviter d'envoyer des erreurs
        if valeur_lue.strip() != "": 
            
            # Si la valeur a changé par rapport à l'ancienne
            if valeur_lue != anciennes_valeurs_pid[parametre]:
                
                # 3. On formate et on envoie
                message = f"{parametre}:{valeur_lue}\n"
                
                if arduino and arduino.is_open:
                    arduino.write(message.encode('utf-8'))
                    print(f"Mise à jour envoyée : {message.strip()}")
                
                # 4. On sauvegarde cette nouvelle valeur comme étant l'ancienne pour la prochaine fois
                anciennes_valeurs_pid[parametre] = valeur_lue
def Cal(poid):
    message = f"Cal:{poid}\n"
    if arduino and arduino.is_open:
        arduino.write(message.encode('utf-8'))
        print(f"Mise à jour envoyée : {message.strip()}")
        if poid == 200:
            tare()

    # Vous pourriez envoyer ça à l'Arduino ici : arduino.write(f"CAL:{cal_value}\n".encode('utf-8'))


# --- 6. Interface Graphique ---
ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("700x700") # Agrandie pour le nouveau menu
app.title("Arduino GUI")

# --- Barre Supérieure (Connexion & Mode) ---
top_frame = ctk.CTkFrame(app)
top_frame.pack(pady=10, padx=20, fill="x")

# Ligne 1: Port, Baudrate, Connecter
port_combobox = ctk.CTkComboBox(top_frame, values=get_available_ports(), width=100)
port_combobox.grid(row=0, column=0, padx=10, pady=10)

baudrate_combobox = ctk.CTkComboBox(top_frame, values=["9600", "115200"], width=90)
baudrate_combobox.grid(row=0, column=1, padx=10, pady=10)
baudrate_combobox.set("115200")

btn_connect = ctk.CTkButton(top_frame, text="Connecter", command=connect_serial, width=90)
btn_connect.grid(row=0, column=2, padx=10, pady=10)

# Ligne 2: Sélection du Mode
mode_label = ctk.CTkLabel(top_frame, text="Vue:")
mode_label.grid(row=0, column=3, padx=(20, 5), pady=10)

mode_combobox = ctk.CTkComboBox(top_frame, values=["Mode Normal", "Mode Setup", "Mode Calibration"], command=change_mode, width=120)
mode_combobox.grid(row=0, column=4, padx=5, pady=10)

# Label de statut global
status_label = ctk.CTkLabel(app, text="Status: En attente de connexion", font=("Roboto", 14))
status_label.pack(pady=5)

# --- Conteneur Principal pour les vues ---
# On crée un conteneur qui va accueillir soit le normal_frame, soit le setup_frame
content_frame = ctk.CTkFrame(app, fg_color="transparent")
content_frame.pack(fill="both", expand=True, padx=20, pady=10)


# === VUE 1 : MODE NORMAL ===
normal_frame = ctk.CTkFrame(content_frame, fg_color="transparent")

instruction_acquisition = ctk.CTkLabel(
    normal_frame,
    text="Connectez vous et cliquez sur 'Acquisition' pour débuter la prise de mesure",
    font=("Roboto", 20, "bold")
)
instruction_acquisition.pack(pady=(10, 20))

data_label = ctk.CTkLabel(normal_frame, text="---", font=("Roboto", 48, "bold"))
data_label.pack(pady=30)

btn_start = ctk.CTkButton(normal_frame, text="Acquisition", command=start_acquisition, fg_color="#27ae60", hover_color="#2ecc71")
btn_start.pack(pady=10)

btn_tare = ctk.CTkButton(normal_frame, text="Tare", command=tare, fg_color="#27ae60", hover_color="#2ecc71")
btn_tare.pack(pady=5)

# On affiche la vue normale par défaut
normal_frame.pack(fill="both", expand=True)


# === VUE 2 : MODE SETUP ===
setup_frame = ctk.CTkFrame(content_frame)

setup_title = ctk.CTkLabel(setup_frame, text="Définir les gains de régulateur", font=("Roboto", 20, "bold"))
setup_title.pack(pady=20)


KpPos_label = ctk.CTkLabel(setup_frame, text="Kp Position:")
KpPos_label.pack(pady=5)

KpPos_entry = ctk.CTkEntry(setup_frame, placeholder_text="Ex: 1.5")
KpPos_entry.pack(pady=5)

KiPos_label = ctk.CTkLabel(setup_frame, text="Ki Position:")
KiPos_label.pack(pady=5)

KiPos_entry = ctk.CTkEntry(setup_frame, placeholder_text="Ex: 1.5")
KiPos_entry.pack(pady=5)

KdPos_label = ctk.CTkLabel(setup_frame, text="Kd Position:")
KdPos_label.pack(pady=5)

KdPos_entry = ctk.CTkEntry(setup_frame, placeholder_text="Ex: 1.5")
KdPos_entry.pack(pady=5)

KpCour_label = ctk.CTkLabel(setup_frame, text="Kp Courant:")
KpCour_label.pack(pady=5)

KpCour_entry = ctk.CTkEntry(setup_frame, placeholder_text="Ex: 1.5")
KpCour_entry.pack(pady=5)

KiCour_label = ctk.CTkLabel(setup_frame, text="Ki Courant:")
KiCour_label.pack(pady=5)

KiCour_entry = ctk.CTkEntry(setup_frame, placeholder_text="Ex: 1.5")
KiCour_entry.pack(pady=5)

btn_Set = ctk.CTkButton(setup_frame, text="Envoyer", command=SetPID)
btn_Set.pack(pady=20)

# === VUE 3 : MODE Calibration ===
Cal_frame = ctk.CTkFrame(content_frame)

instruction_calibration = ctk.CTkLabel(
    Cal_frame,
    text = "Déposez une masse puis cliquez sur la valeur de cette masse pour enregistrer le point. " \
    "Cliquez sur 'Envoyer' une fois que tous les points ont été enregistrés.",
    font=("Roboto", 15, "bold"),
    wraplength=500,
    justify="center"
)
instruction_calibration.pack(pady=(10, 20))


btn_Zero = ctk.CTkButton(Cal_frame, text="0g", command=lambda:Cal(0), fg_color="#27ae60", hover_color="#2ecc71")
btn_Zero.pack(pady=5)

btn_50 = ctk.CTkButton(Cal_frame, text="50g", command=lambda:Cal(50), fg_color="#27ae60", hover_color="#2ecc71")
btn_50.pack(pady=5)

btn_100 = ctk.CTkButton(Cal_frame, text="100g", command=lambda:Cal(100), fg_color="#27ae60", hover_color="#2ecc71")
btn_100.pack(pady=5)

btn_Done = ctk.CTkButton(Cal_frame, text="Envoyer", command=lambda:Cal(200), fg_color="#27ae60", hover_color="#2ecc71")
btn_Done.pack(pady=5)

# Fermeture propre
def on_closing():
    global is_acquiring
    is_acquiring = False
    if arduino and arduino.is_open:
        arduino.close()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()