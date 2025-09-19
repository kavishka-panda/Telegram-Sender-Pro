import customtkinter as ctk
from telethon import TelegramClient
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os

# --- Global Variables for Async Tasks ---
# For communication between the UI and the Async Task
client = None
executor = ThreadPoolExecutor(max_workers=1)
SESSION_FILE = 'group_sender_session.session'
JOURNAL_FILE = 'group_sender_session.session-journal'

# --- Asynchronous Telegram Functions ---
# These functions can be outside the UI class.

async def get_groups_async(app_instance):
    """Fetches the list of all groups."""
    global client
    
    groups = []
    async for d in client.iter_dialogs():
        # Selects only groups or supergroups
        if d.is_group and d.title is not None:
             # For displaying the Title
            groups.append((d.entity, d.title)) 
    print(f"Groups found: {len(groups)}")
    return groups

async def send_message_to_groups(app_instance, message_text, delay_seconds, groups_list):
    """Sends the message to groups according to the specified delay."""
    global client
    # The fix is to check the connection status without a second await
    try:
        is_connected_result = await client.is_connected()
    except TypeError:
        # The is_connected() returned a bool, not a coroutine, so we just use its value.
        is_connected_result = client.is_connected()
        
    if not is_connected_result:
        await client.start()
    
    app_instance.stop_requested = False
    
    for entity, title in groups_list:
        if app_instance.stop_requested:
            app_instance.log_to_textbox("\n--- Process stopped by user! ---")
            break
            
        try:
            # Send the message
            await client.send_message(entity, message_text)
            
            # Update the log
            # This process should happen in the UI thread, so it must be called from a UI method.
            app_instance.log_to_textbox(f"✅ Sent to: {title}")
            
            # Add the specified delay
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            
        except Exception as e:
            app_instance.log_to_textbox(f"❌ Error sending to {title}: {e}")
            await asyncio.sleep(5) # Adds a small delay if there's an error
    else: # This block runs if the for loop completes without a 'break'
        app_instance.log_to_textbox("\n--- All messages sent successfully! ---")

async def attempt_telethon_login(app_instance, api_id, api_hash):
    """Handles the async login process with Telethon."""
    global client
    try:
        # Check if client exists and is connected, if not, create a new one.
        if client:
            try:
                is_connected_result = await client.is_connected()
            except TypeError:
                is_connected_result = client.is_connected()
            
            if is_connected_result:
                return "authorized"
            
        client = TelegramClient(SESSION_FILE, api_id, api_hash)
        await client.connect()
        
        if await client.is_user_authorized():
            return "authorized"
        else:
            return "phone_required"
    except Exception as e:
        return f"Error: {e}"

async def send_phone_code(app_instance, phone_number):
    """Sends the verification code to the given phone number."""
    global client
    try:
        app_instance.sent_code_hash = (await client.send_code_request(phone_number)).phone_code_hash
        return "code_sent"
    except Exception as e:
        return f"Error: {e}"

async def verify_phone_code(app_instance, phone_number, phone_code):
    """Verifies the phone code to complete login."""
    global client
    try:
        await client.sign_in(phone=phone_number, code=phone_code, phone_code_hash=app_instance.sent_code_hash)
        if await client.is_user_authorized():
            return "authorized"
        else:
            return "Failed to sign in."
    except Exception as e:
        return f"Error: {e}"

# --- CustomTkinter UI Class ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Settings
        self.title("Telegram Group Sender")
        self.geometry("600x650")

        # Configure grid layout
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)

        # Variables
        self.groups_data = []
        self.delay_var = ctk.StringVar(value="60")
        self.stop_requested = False
        self.sent_code_hash = None
        self.phone_number = None
        
        # Initial login frame
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.login_label = ctk.CTkLabel(self.login_frame, text="Enter Telegram API Credentials", font=ctk.CTkFont(size=20, weight="bold"))
        self.login_label.pack(pady=20)

        self.api_id_entry = ctk.CTkEntry(self.login_frame, placeholder_text="API ID", width=300)
        self.api_id_entry.pack(pady=10)
        
        self.api_hash_entry = ctk.CTkEntry(self.login_frame, placeholder_text="API Hash", width=300)
        self.api_hash_entry.pack(pady=10)
        
        self.login_button = ctk.CTkButton(self.login_frame, text="Connect to Telegram", command=self.attempt_login)
        self.login_button.pack(pady=20)

        self.login_status_label = ctk.CTkLabel(self.login_frame, text="")
        self.login_status_label.pack(pady=10)
        
        # Phone and Code frame (will be created later)
        self.phone_frame = None
        
        # Main UI frame (hidden initially)
        self.main_ui_frame = ctk.CTkFrame(self)
        
        # Main UI elements
        self.msg_label = ctk.CTkLabel(self.main_ui_frame, text="Message to Send:")
        self.msg_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.msg_textbox = ctk.CTkTextbox(self.main_ui_frame, height=150)
        self.msg_textbox.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.delay_frame = ctk.CTkFrame(self.main_ui_frame)
        self.delay_frame.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="ew")
        self.delay_frame.grid_columnconfigure((0, 2), weight=1)
        
        self.delay_label = ctk.CTkLabel(self.delay_frame, text="Delay (seconds) between messages:")
        self.delay_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.delay_entry = ctk.CTkEntry(self.delay_frame, textvariable=self.delay_var, width=100)
        self.delay_entry.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        self.groups_info = ctk.CTkLabel(self.delay_frame, text="Groups: Loading...")
        self.groups_info.grid(row=0, column=2, padx=10, pady=10, sticky="e")
        
        self.button_frame = ctk.CTkFrame(self.main_ui_frame)
        self.button_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.send_button = ctk.CTkButton(self.button_frame, text="🚀 Start Sending", command=self.start_sending, state="disabled")
        self.send_button.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
        self.stop_button = ctk.CTkButton(self.button_frame, text="🛑 Stop Sending", command=self.stop_sending, state="disabled", fg_color="#d62828")
        self.stop_button.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.logout_button = ctk.CTkButton(self.button_frame, text="Logout", command=self.logout_user, fg_color="#5e5e5e")
        self.logout_button.grid(row=0, column=2, padx=5, pady=10, sticky="ew")


        self.log_label = ctk.CTkLabel(self.main_ui_frame, text="Activity Log:")
        self.log_label.grid(row=4, column=0, padx=20, pady=(0, 5), sticky="w")
        self.log_textbox = ctk.CTkTextbox(self.main_ui_frame, height=200)
        self.log_textbox.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_textbox.configure(state="disabled")
        
        self.check_session()

    def check_session(self):
        """Checks for an existing session file and logs in automatically."""
        if os.path.exists(SESSION_FILE):
            self.login_status_label.configure(text="Found existing session. Please click 'Connect' to log in automatically.", text_color="yellow")
            # We don't try to connect immediately. We let the user re-enter the credentials if they want,
            # or simply click the connect button to use the session.
        else:
            self.login_status_label.configure(text="Enter API Credentials to start.", text_color="gray")

    def log_to_textbox(self, text):
        """Adds messages to the UI Log Textbox."""
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", text + "\n")
        self.log_textbox.see("end") # scrolls to show the latest message
        self.log_textbox.configure(state="disabled")

    def attempt_login(self):
        """Initial attempt to connect using API credentials."""
        api_id_str = self.api_id_entry.get()
        api_hash = self.api_hash_entry.get()

        if os.path.exists(SESSION_FILE):
            # If a session file exists, we can log in with or without credentials
            # but we'll try with the provided ones if they exist
            api_id = int(api_id_str) if api_id_str else 0
            api_hash = api_hash if api_hash else "dummy" # dummy hash for reconnect
        elif not api_id_str or not api_hash:
            self.login_status_label.configure(text="Please enter both API ID and Hash.", text_color="red")
            return
        else:
            api_id = int(api_id_str)


        try:
            self.login_status_label.configure(text="Connecting...", text_color="yellow")
            self.login_button.configure(state="disabled", text="Connecting...")
            executor.submit(self._run_async, attempt_telethon_login(self, api_id, api_hash)).add_done_callback(self._handle_login_result)
        except ValueError:
            self.login_status_label.configure(text="Invalid API ID. It must be a number.", text_color="red")
            self.login_button.configure(state="normal", text="Connect to Telegram")
    
    def _handle_login_result(self, future):
        """Handles the result of the initial login attempt."""
        try:
            result = future.result()
            if result == "authorized":
                self.login_status_label.configure(text="Successfully connected!", text_color="green")
                self.after(100, self.show_main_ui)
            elif result == "phone_required":
                self.login_status_label.configure(text="Please enter your phone number.", text_color="yellow")
                self.after(100, self.show_phone_entry_ui)
            else:
                self.login_status_label.configure(text=f"Connection Error: {result}", text_color="red")
                self.login_button.configure(state="normal", text="Connect to Telegram")
        except Exception as e:
            self.login_status_label.configure(text=f"Connection Error: {e}", text_color="red")
            self.login_button.configure(state="normal", text="Connect to Telegram")
    
    def show_phone_entry_ui(self):
        """Transitions the UI to the phone number and code entry screen."""
        self.login_frame.destroy()
        
        self.phone_frame = ctk.CTkFrame(self)
        self.phone_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.phone_label = ctk.CTkLabel(self.phone_frame, text="Enter your phone number (e.g., +1234567890)", font=ctk.CTkFont(size=16, weight="bold"))
        self.phone_label.pack(pady=(20, 5))
        
        self.phone_entry = ctk.CTkEntry(self.phone_frame, placeholder_text="Phone Number", width=300)
        self.phone_entry.pack(pady=10)
        
        self.phone_button = ctk.CTkButton(self.phone_frame, text="Send Code", command=self.handle_phone_entry)
        self.phone_button.pack(pady=10)

        self.code_label = ctk.CTkLabel(self.phone_frame, text="Enter the verification code:", font=ctk.CTkFont(size=16, weight="bold"))
        self.code_label.pack_forget()

        self.code_entry = ctk.CTkEntry(self.phone_frame, placeholder_text="Code", width=300)
        self.code_entry.pack_forget()
        
        self.code_button = ctk.CTkButton(self.phone_frame, text="Verify Code", command=self.handle_code_entry)
        self.code_button.pack_forget()

        self.login_status_label = ctk.CTkLabel(self.phone_frame, text="")
        self.login_status_label.pack(pady=10)

    def handle_phone_entry(self):
        """Handles the phone number submission."""
        self.phone_number = self.phone_entry.get().strip()
        if not self.phone_number:
            self.login_status_label.configure(text="Please enter a valid phone number.", text_color="red")
            return

        self.phone_button.configure(state="disabled", text="Sending...")
        self.login_status_label.configure(text="Sending code...", text_color="yellow")
        executor.submit(self._run_async, send_phone_code(self, self.phone_number)).add_done_callback(self._handle_phone_code_result)

    def _handle_phone_code_result(self, future):
        """Handles the result of the code sending attempt."""
        result = future.result()
        if result == "code_sent":
            self.phone_button.configure(state="normal", text="Send Code")
            self.code_label.pack(pady=(20, 5))
            self.code_entry.pack(pady=10)
            self.code_button.pack(pady=10)
        else:
            self.login_status_label.configure(text=f"Error: {result}", text_color="red")
            self.phone_button.configure(state="normal", text="Send Code")
    
    def handle_code_entry(self):
        """Handles the verification code submission."""
        phone_code = self.code_entry.get().strip()
        if not phone_code:
            self.login_status_label.configure(text="Please enter the code.", text_color="red")
            return
        
        self.code_button.configure(state="disabled", text="Verifying...")
        self.login_status_label.configure(text="Verifying...", text_color="yellow")
        executor.submit(self._run_async, verify_phone_code(self, self.phone_number, phone_code)).add_done_callback(self._handle_code_verification_result)
        
    def _handle_code_verification_result(self, future):
        """Handles the result of the code verification."""
        result = future.result()
        if result == "authorized":
            self.login_status_label.configure(text="Login successful!", text_color="green")
            self.after(100, self.show_main_ui)
        else:
            self.login_status_label.configure(text=f"Login failed: {result}", text_color="red")
            self.code_button.configure(state="normal", text="Verify Code")
    
    def show_main_ui(self):
        """Destroys the login UI and shows the main app UI."""
        # Check which frame is currently packed and destroy it
        for widget in self.winfo_children():
            if isinstance(widget, ctk.CTkFrame):
                widget.destroy()
        
        self.main_ui_frame = ctk.CTkFrame(self)
        self.main_ui_frame.pack(fill="both", expand=True)
        self.main_ui_frame.grid_columnconfigure(0, weight=1)
        self.main_ui_frame.grid_rowconfigure(5, weight=1)

        # Recreate the UI elements on the new frame
        self.msg_label = ctk.CTkLabel(self.main_ui_frame, text="Message to Send:")
        self.msg_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.msg_textbox = ctk.CTkTextbox(self.main_ui_frame, height=150)
        self.msg_textbox.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.delay_frame = ctk.CTkFrame(self.main_ui_frame)
        self.delay_frame.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="ew")
        self.delay_frame.grid_columnconfigure((0, 2), weight=1)
        
        self.delay_label = ctk.CTkLabel(self.delay_frame, text="Delay (seconds) between messages:")
        self.delay_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.delay_entry = ctk.CTkEntry(self.delay_frame, textvariable=self.delay_var, width=100)
        self.delay_entry.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        self.groups_info = ctk.CTkLabel(self.delay_frame, text="Groups: Loading...")
        self.groups_info.grid(row=0, column=2, padx=10, pady=10, sticky="e")
        
        self.button_frame = ctk.CTkFrame(self.main_ui_frame)
        self.button_frame.grid(row=3, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.send_button = ctk.CTkButton(self.button_frame, text="🚀 Start Sending", command=self.start_sending, state="disabled")
        self.send_button.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
        self.stop_button = ctk.CTkButton(self.button_frame, text="🛑 Stop Sending", command=self.stop_sending, state="disabled", fg_color="#d62828")
        self.stop_button.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.logout_button = ctk.CTkButton(self.button_frame, text="Logout", command=self.logout_user, fg_color="#5e5e5e")
        self.logout_button.grid(row=0, column=2, padx=5, pady=10, sticky="ew")


        self.log_label = ctk.CTkLabel(self.main_ui_frame, text="Activity Log:")
        self.log_label.grid(row=4, column=0, padx=20, pady=(0, 5), sticky="w")
        self.log_textbox = ctk.CTkTextbox(self.main_ui_frame, height=200)
        self.log_textbox.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="nsew")
        self.log_textbox.configure(state="disabled")

        self.load_groups()

    def logout_user(self):
        """Disconnects the client and returns to the login screen."""
        self.log_to_textbox("Logging out...")
        # Use the executor to run the async logout function
        executor.submit(self._run_async, self._perform_logout_async()).add_done_callback(self._handle_logout_complete)

    async def _perform_logout_async(self):
        """Async function to handle the Telethon logout."""
        global client
        try:
            if client and client.is_connected():
                await client.log_out()
                return "success"
            else:
                return "not_connected"
        except Exception as e:
            # Fallback to manual removal if log_out fails
            return f"Error: {e}"
        finally:
            if os.path.exists(SESSION_FILE):
                os.remove(SESSION_FILE)
            if os.path.exists(JOURNAL_FILE):
                os.remove(JOURNAL_FILE)
    
    def _handle_logout_complete(self, future):
        """Handles the result of the async logout operation."""
        try:
            result = future.result()
            if result == "success":
                self.log_to_textbox("Logout successful. Session file removed.")
            elif result == "not_connected":
                self.log_to_textbox("Client was not connected. Session file removed.")
            else:
                self.log_to_textbox(f"Logout failed: {result}. Session file manually removed.")
        except Exception as e:
            self.log_to_textbox(f"An unexpected error occurred during logout: {e}")
        finally:
            self.after(0, self.reset_ui_to_login)

    def reset_ui_to_login(self):
        """Resets the UI back to the initial login screen."""
        self.main_ui_frame.destroy()
        
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.login_label = ctk.CTkLabel(self.login_frame, text="Enter Telegram API Credentials", font=ctk.CTkFont(size=20, weight="bold"))
        self.login_label.pack(pady=20)
        self.api_id_entry = ctk.CTkEntry(self.login_frame, placeholder_text="API ID", width=300)
        self.api_id_entry.pack(pady=10)
        self.api_hash_entry = ctk.CTkEntry(self.login_frame, placeholder_text="API Hash", width=300)
        self.api_hash_entry.pack(pady=10)
        self.login_button = ctk.CTkButton(self.login_frame, text="Connect to Telegram", command=self.attempt_login)
        self.login_button.pack(pady=20)
        self.login_status_label = ctk.CTkLabel(self.login_frame, text="")
        self.login_status_label.pack(pady=10)

        self.login_status_label.configure(text="Logged out. Please log in again.", text_color="green")


    def load_groups(self):
        """Asynchronously loads Telegram Groups."""
        self.groups_info.configure(text="Groups: Fetching...")
        self.log_to_textbox("Connecting to Telegram and fetching groups...")
        
        executor.submit(self._run_async, get_groups_async(self)).add_done_callback(self._groups_loaded_callback)

    def _groups_loaded_callback(self, future):
        """Updates the UI after groups are loaded."""
        try:
            self.groups_data = future.result()
            count = len(self.groups_data)
            self.groups_info.configure(text=f"Groups Found: {count}")
            self.log_to_textbox(f"Successfully loaded {count} groups.")
        except Exception as e:
            self.groups_info.configure(text="Groups: Error!")
            self.log_to_textbox(f"Connection Error: {e}")
        finally:
            self.send_button.configure(state="normal")

    def start_sending(self):
        """Executes when the Send Button is pressed."""
        message = self.msg_textbox.get("1.0", "end-1c").strip()
        try:
            delay = int(self.delay_var.get())
        except ValueError:
            self.log_to_textbox("❌ Error: Invalid delay value. Please use a number.")
            return

        if not self.groups_data:
            self.log_to_textbox("❌ Error: No groups loaded. Check connection.")
            return
        
        if not message:
            self.log_to_textbox("❌ Error: Message cannot be empty.")
            return

        # Disables the UI and starts the Sending Process
        self.send_button.configure(state="disabled", text="Sending...")
        self.stop_button.configure(state="normal")
        self.log_to_textbox(f"\n--- Starting sending process (Delay: {delay}s) ---")
        
        # Asynchronously run the send_message_to_groups function
        executor.submit(
            self._run_async, 
            send_message_to_groups(self, message, delay, self.groups_data)
        ).add_done_callback(self._sending_finished_callback)

    def stop_sending(self):
        """Signals the ongoing process to stop."""
        self.stop_requested = True
        self.stop_button.configure(state="disabled", text="Stopping...")
        self.send_button.configure(state="disabled")

    def _sending_finished_callback(self, future):
        """Resets the UI after the sending process is finished."""
        self.send_button.configure(state="normal", text="🚀 Start Sending")
        self.stop_button.configure(state="disabled", text="🛑 Stop Sending")
        
        # Check if an exception occurred during the process
        if future.exception():
            self.log_to_textbox(f"❌ Critical Error during sending: {future.exception()}")

    def _run_async(self, coro):
        """Runs an Async function within an Event Loop."""
        try:
            # Attempts to get the Event Loop for the current Thread.
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If no Event Loop exists, creates a new one and sets it.
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        # Runs the Coroutine in the Loop.
        return loop.run_until_complete(coro)

# --- Application Main Run ---
if __name__ == "__main__":
    # Creates the App as a global variable.
    app = App()
    app.mainloop() 
    # Disconnects the Telegram Client when the Application closes.
    if client:
        executor.submit(client.disconnect)
    executor.shutdown()
