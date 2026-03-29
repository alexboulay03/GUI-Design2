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
        valeur_en_grammes = float(data)
        unite_actuelle = menu_unite.get()
        
        # Appel de la fonction de conversion
        valeur_convertie = convertir_poids(valeur_en_grammes, unite_actuelle)
        
        # Mise à jour de l'affichage avec 2 décimales et la bonne unité
        data_label.configure(text=f"{valeur_convertie:.1f} {unite_actuelle}")
    except ValueError:
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
        app.after(500, tare)

def convertir_poids(valeur_g, unite_cible):
    """Convertit les grammes vers l'unité sélectionnée."""
    if unite_cible == "oz":
        return valeur_g * 0.03527396
    elif unite_cible == "N":
        # Force = masse (en kg) * accélération (gravité)
        return (valeur_g / 1000.0) * 9.80665
    else:
        # Par défaut, on retourne les grammes
        return valeur_g

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
    # 1. On commence par cacher TOUTES les frames pour faire place nette
    normal_frame.pack_forget()
    setup_frame.pack_forget()
    Cal_frame.pack_forget()
    if choice == "Mode Normal":
        # Cacher le setup, afficher le normal
        setup_frame.pack_forget()
        Cal_frame.pack_forget()
        normal_frame.pack(fill="both", expand=True, pady=10)
    elif choice == "Mode Setup":
        setup_frame.pack(fill="both", expand=True, pady=10)
    elif choice == "Mode Calibration":
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
            app.after(500, tare)

    # Vous pourriez envoyer ça à l'Arduino ici : arduino.write(f"CAL:{cal_value}\n".encode('utf-8'))


# --- 6. Interface Graphique ---
ctk.set_appearance_mode("dark")  
ctk.set_default_color_theme("blue")

app = ctk.CTk()
app.geometry("900x700") # Agrandie pour le nouveau menu
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
    text="Cliquez sur 'Connecter' et puis sur 'Acquisition' " \
    "pour débuter la prise de mesure",
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

setup_title = ctk.CTkLabel(setup_frame, text="Définir les gains de chaque régulateur", font=("Roboto", 20, "bold"))
setup_title.pack(pady=20)


KpPos_label = ctk.CTkLabel(setup_frame, text="Kp Position:")
KpPos_label.pack(pady=5)

KpPos_entry = ctk.CTkEntry(setup_frame, placeholder_text="0.15")
KpPos_entry.pack(pady=5)

KiPos_label = ctk.CTkLabel(setup_frame, text="Ki Position:")
KiPos_label.pack(pady=5)

KiPos_entry = ctk.CTkEntry(setup_frame, placeholder_text="2.3")
KiPos_entry.pack(pady=5)

KdPos_label = ctk.CTkLabel(setup_frame, text="Kd Position:")
KdPos_label.pack(pady=5)

KdPos_entry = ctk.CTkEntry(setup_frame, placeholder_text="0.02")
KdPos_entry.pack(pady=5)

KpCour_label = ctk.CTkLabel(setup_frame, text="Kp Courant:")
KpCour_label.pack(pady=5)

KpCour_entry = ctk.CTkEntry(setup_frame, placeholder_text="0.25")
KpCour_entry.pack(pady=5)

KiCour_label = ctk.CTkLabel(setup_frame, text="Ki Courant:")
KiCour_label.pack(pady=5)

KiCour_entry = ctk.CTkEntry(setup_frame, placeholder_text="2.4")
KiCour_entry.pack(pady=5)

btn_Set = ctk.CTkButton(setup_frame, text="Envoyer", command=SetPID)
btn_Set.pack(pady=20)

# === VUE 3 : MODE Calibration ===
Cal_frame = ctk.CTkFrame(content_frame)
# Liste initiale des poids pour le menu déroulant
valeurs_poids = ["0", "20", "40", "60", "80", "100"]
instruction_calibration = ctk.CTkLabel(
    Cal_frame,
    text = "Pour calibrer, déposez une masse puis enregistrez le point en indiquant la valeur de cette masse. " \
    ""\
    "Cliquez sur 'Envoyer' une fois que tous les points sont enregistrés. Une fois envoyé, " \
    "retirer les masses de la balance",
    font=("Roboto", 15, "bold"),
    wraplength=500,
    justify="center"
)
instruction_calibration.pack(pady=(10, 20))

def envoyer_poids_selectionne():
    # 1. Récupère la valeur sélectionnée dans le menu déroulant
    selection = menu_poids.get()
    
    # 2. Extrait le nombre brut (enlève le " ✓" s'il a déjà été cliqué)
    poids_brut = selection.replace(" ✓", "")
    
    # 3. Envoie la commande à l'Arduino via ta fonction existante
    Cal(int(poids_brut))
    
    # 4. Met à jour la liste pour ajouter le crochet à côté de ce poids
    for i in range(len(valeurs_poids)):
        # On cherche l'élément correspondant au poids brut
        if valeurs_poids[i].replace(" ✓", "") == poids_brut:
            valeurs_poids[i] = f"{poids_brut} ✓"
            
    # 5. Met à jour le menu déroulant avec les nouvelles valeurs (avec le crochet)
    menu_poids.configure(values=valeurs_poids)
    menu_poids.set(f"{poids_brut} ✓") # Garde la sélection actuelle visible à l'écran


# --- Éléments de l'interface ---

# Menu déroulant (Drop down menu)
menu_poids = ctk.CTkOptionMenu(Cal_frame, values=valeurs_poids, width=150)
menu_poids.pack(pady=15)
menu_poids.set("0") # Valeur par défaut affichée

# Bouton pour envoyer le poids spécifique sélectionné dans le menu
btn_Envoyer_Poids = ctk.CTkButton(Cal_frame, text="Envoyer la masse sélectionnée", command=envoyer_poids_selectionne, fg_color="#3498db", hover_color="#2980b9")
btn_Envoyer_Poids.pack(pady=10)

# Espace de séparation visuelle (optionnel mais plus propre)
separation = ctk.CTkFrame(Cal_frame, height=2, width=200, fg_color="gray")
separation.pack(pady=15)

# Confirmer l'enovoie des masses/courant
def envoyer_calibration():
    valeurs_attendues = ["0 ✓", "20 ✓", "40 ✓", "60 ✓", "80 ✓", "100 ✓"]
    
    if all(valeur in valeurs_poids for valeur in valeurs_attendues):
        Cal(200)
        status_label.configure(text="Status: Calibration effectuée", text_color="#2ecc71")
        app.after(1000, executer_cal_et_tare)
    else:
        status_label.configure(text="Erreur: Il manque une mesure de masse", text_color="#e74c3c")

# Bouton de validation finale (Garde ta fonction Cal(200))
#btn_Done = ctk.CTkButton(Cal_frame, text="Envoyer (Terminer)", command=lambda:Cal(200), fg_color="#27ae60", hover_color="#2ecc71")
btn_Done = ctk.CTkButton(
    Cal_frame,
    text="Envoyer (Terminer)",
    command=envoyer_calibration,
    fg_color="#27ae60",
    hover_color="#2ecc71"
)
btn_Done.pack(pady=10)


def on_unite_change(nouvelle_unite):
    """Met à jour l'affichage immédiatement quand on change d'unité via le menu."""
    global latest_reading
    try:
        valeur_en_grammes = float(latest_reading)
        valeur_convertie = convertir_poids(valeur_en_grammes, nouvelle_unite)
        data_label.configure(text=f"{valeur_convertie:.1f} {nouvelle_unite}")
    except ValueError:
        pass # Ignore si aucune donnée valide n'a encore été reçue

# Menu déroulant (Drop down menu) pour les unités
unites_disponibles = ["g", "oz", "N"]
menu_unite = ctk.CTkOptionMenu(
    normal_frame, 
    values=unites_disponibles, 
    width=150, 
    command=on_unite_change # Appelle la fonction lors du changement
)
menu_unite.pack(pady=15)
menu_unite.set("g") # Valeur par défaut

# Fermeture propre
def on_closing():
    global is_acquiring
    is_acquiring = False
    if arduino and arduino.is_open:
        arduino.close()
    app.destroy()

app.protocol("WM_DELETE_WINDOW", on_closing)
app.mainloop()