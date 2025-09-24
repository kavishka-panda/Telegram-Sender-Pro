import customtkinter as ctk
from telethon import TelegramClient
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import json
import sys

# --- Global Variables for Async Tasks ---
# For communication between the UI and the Async Task
client = None
executor = ThreadPoolExecutor(max_workers=1)
SESSION_FILE_PREFIX = 'group_sender_session_'
ACCOUNTS_FILE = 'accounts.json'

# --- Asynchronous Telegram Functions ---
# These functions can be outside the UI class.

async def get_groups_async(app_instance):
    """Fetches the list of all groups."""
    global client
    
    # Check connection status without 'await' if it's not a coroutine
    is_connected = False
    try:
        is_connected = await client.is_connected()
    except TypeError:
        is_connected = client.is_connected()

    if not client or not is_connected:
        await client.start()
        
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
    
    is_connected = False
    try:
        is_connected = await client.is_connected()
    except TypeError:
        is_connected = client.is_connected()

    if not is_connected:
        await client.start()
    
    app_instance.stop_requested = False
    
    for entity, title in groups_list:
        if app_instance.stop_requested:
            app_instance.log_to_textbox("\n--- Process stopped by user! ---")
            break
            
        try:
            # Send the message
            await client.send_message(entity, message_text)
            
            # Update the log and sent count
            # Use app_instance.after() to safely update the UI from this thread
            app_instance.after(0, lambda t=title: app_instance.log_to_textbox(f"✅ Sent to: {t}"))
            app_instance.after(0, app_instance.increment_sent_count)
            
            # Add the specified delay
            if delay_seconds > 0:
                await asyncio.sleep(delay_seconds)
            
        except Exception as e:
            app_instance.after(0, lambda t=title, err=e: app_instance.log_to_textbox(f"❌ Error sending to {t}: {err}"))
            await asyncio.sleep(5) # Adds a small delay if there's an error
    else: # This block runs if the for loop completes without a 'break'
        app_instance.after(0, lambda: app_instance.log_to_textbox("\n--- All messages sent successfully! ---"))

async def attempt_telethon_login(app_instance, api_id, api_hash, phone_number):
    """Handles the async login process with Telethon."""
    global client
    try:
        session_file = f"{SESSION_FILE_PREFIX}{phone_number}"
        
        # If a client already exists from a previous session, disconnect it first.
        if client:
            try:
                if await client.is_connected():
                    await client.disconnect()
            except TypeError:
                 if client.is_connected():
                    await client.disconnect()
            
        client = TelegramClient(session_file, api_id, api_hash)
        
        # Check connection status without 'await' if it's not a coroutine
        is_connected = False
        try:
            is_connected = await client.is_connected()
        except TypeError:
            is_connected = client.is_connected()

        if not is_connected:
            await client.connect()
        
        is_user_authorized = False
        try:
            is_user_authorized = await client.is_user_authorized()
        except TypeError:
            is_user_authorized = client.is_user_authorized()

        if is_user_authorized:
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
        
        is_user_authorized = False
        try:
            is_user_authorized = await client.is_user_authorized()
        except TypeError:
            is_user_authorized = client.is_user_authorized()

        if is_user_authorized:
            return "authorized"
        else:
            return "Failed to sign in."
    except Exception as e:
        return f"Error: {e}"
        
# --- Data Management Functions ---
def load_accounts():
    """Loads accounts from the JSON file."""
    if os.path.exists(ACCOUNTS_FILE):
        with open(ACCOUNTS_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}

def save_accounts(accounts):
    """Saves accounts to the JSON file."""
    with open(ACCOUNTS_FILE, 'w') as f:
        json.dump(accounts, f, indent=4)

# --- CustomTkinter UI Class ---
class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Window Settings
        self.title("Telegram Group Sender")
        # කවුළුවේ ප්‍රමාණය 400x450 දක්වා අඩු කිරීම. (Reducing the window size to 400x450.)
        self.geometry("400x450")

        # Variables
        self.groups_data = []
        self.delay_var = ctk.StringVar(value="60")
        self.stop_requested = False
        self.sent_code_hash = None
        self.phone_number = None
        self.accounts = load_accounts()
        self.sent_count = 0
        
        # Initial UI setup
        self.show_account_selection_ui()
        
    def show_account_selection_ui(self):
        """Shows the UI for selecting or adding an account."""
        for widget in self.winfo_children():
            widget.destroy()

        self.account_frame = ctk.CTkFrame(self)
        self.account_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(self.account_frame, text="Select an Account", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))
        
        # Accounts list frame (with scrollbar)
        self.account_list_frame = ctk.CTkScrollableFrame(self.account_frame)
        self.account_list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.update_account_list()
        
        ctk.CTkButton(self.account_frame, text="Add New Account", command=self.show_add_account_ui).pack(pady=10)
        ctk.CTkLabel(self.account_frame, text="Log:").pack(pady=(10, 5))
        self.status_label = ctk.CTkLabel(self.account_frame, text="Add a new account or select an existing one.")
        self.status_label.pack(pady=5)
        
    def update_account_list(self):
        """Refreshes the list of accounts on the UI."""
        for widget in self.account_list_frame.winfo_children():
            widget.destroy()
            
        if not self.accounts:
            ctk.CTkLabel(self.account_list_frame, text="No accounts saved yet.").pack(pady=20)
            return

        for phone, details in self.accounts.items():
            account_row_frame = ctk.CTkFrame(self.account_list_frame, fg_color="transparent")
            account_row_frame.pack(fill="x", padx=5, pady=5)
            account_row_frame.grid_columnconfigure(0, weight=1)
            
            phone_button = ctk.CTkButton(account_row_frame, text=phone, 
                                          command=lambda p=phone, d=details: self.attempt_login(p, d))
            phone_button.grid(row=0, column=0, sticky="ew", padx=(0, 5))

            delete_button = ctk.CTkButton(account_row_frame, text="Delete", fg_color="#d62828",
                                          command=lambda p=phone: self.delete_account(p))
            delete_button.grid(row=0, column=1, padx=(5, 0))
    
    def delete_account(self, phone):
        """Deletes an account from the dictionary and the JSON file."""
        if phone in self.accounts:
            del self.accounts[phone]
            save_accounts(self.accounts)
            
            # Delete the session file as well
            session_file = f"{SESSION_FILE_PREFIX}{phone}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
            
            self.status_label.configure(text=f"Account {phone} deleted.")
            self.update_account_list()

    def show_add_account_ui(self):
        """Shows the UI for adding a new account."""
        self.add_account_window = ctk.CTkToplevel(self)
        self.add_account_window.title("Add New Account")
        self.add_account_window.geometry("400x300")
        self.add_account_window.grab_set()
        
        ctk.CTkLabel(self.add_account_window, text="Enter New Account Details", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        
        self.new_api_id_entry = ctk.CTkEntry(self.add_account_window, placeholder_text="API ID", width=300)
        self.new_api_id_entry.pack(pady=5)
        self.new_api_hash_entry = ctk.CTkEntry(self.add_account_window, placeholder_text="API Hash", width=300)
        self.new_api_hash_entry.pack(pady=5)
        self.new_phone_entry = ctk.CTkEntry(self.add_account_window, placeholder_text="Phone Number (e.g., +1234567890)", width=300)
        self.new_phone_entry.pack(pady=5)
        
        ctk.CTkButton(self.add_account_window, text="Save Account", command=self.save_new_account).pack(pady=20)
        
        self.add_status_label = ctk.CTkLabel(self.add_account_window, text="")
        self.add_status_label.pack(pady=5)

    def save_new_account(self):
        """Saves a new account to the dictionary and the JSON file."""
        api_id_str = self.new_api_id_entry.get().strip()
        api_hash = self.new_api_hash_entry.get().strip()
        phone_number = self.new_phone_entry.get().strip()

        if not api_id_str or not api_hash or not phone_number:
            self.add_status_label.configure(text="All fields are required.", text_color="red")
            return
        
        try:
            api_id = int(api_id_str)
        except ValueError:
            self.add_status_label.configure(text="Invalid API ID. Must be a number.", text_color="red")
            return

        if phone_number in self.accounts:
            self.add_status_label.configure(text="Account already exists.", text_color="red")
            return

        self.accounts[phone_number] = {"api_id": api_id, "api_hash": api_hash}
        save_accounts(self.accounts)
        self.add_status_label.configure(text="Account saved successfully!", text_color="green")
        self.add_account_window.destroy()
        self.update_account_list()

    def log_to_textbox(self, text):
        """Adds messages to the UI Log Textbox."""
        if hasattr(self, 'log_textbox'):
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", text + "\n")
            self.log_textbox.see("end") # scrolls to show the latest message
            self.log_textbox.configure(state="disabled")

    def increment_sent_count(self):
        """Increments the sent message count and updates the UI label."""
        self.sent_count += 1
        if hasattr(self, 'sent_count_label'):
            self.sent_count_label.configure(text=f"Sent: {self.sent_count}")

    def attempt_login(self, phone_number, details):
        """Initial attempt to connect using stored credentials."""
        self.phone_number = phone_number
        api_id = details["api_id"]
        api_hash = details["api_hash"]
        
        self.status_label.configure(text=f"Connecting to {self.phone_number}...", text_color="yellow")
        
        executor.submit(self._run_async, attempt_telethon_login(self, api_id, api_hash, self.phone_number)).add_done_callback(self._handle_login_result)
    
    def _handle_login_result(self, future):
        """Handles the result of the initial login attempt."""
        try:
            result = future.result()
            if result == "authorized":
                self.status_label.configure(text="Successfully connected!", text_color="green")
                self.after(100, self.show_main_ui)
            elif result == "phone_required":
                self.status_label.configure(text=f"Please enter the code sent to {self.phone_number}.", text_color="yellow")
                self.after(100, self.show_code_entry_ui)
            else:
                self.status_label.configure(text=f"Connection Error: {result}", text_color="red")
        except Exception as e:
            self.status_label.configure(text=f"Connection Error: {e}", text_color="red")
    
    def show_code_entry_ui(self):
        """Transitions the UI to the verification code entry screen."""
        self.account_frame.destroy()
        
        self.phone_frame = ctk.CTkFrame(self)
        self.phone_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(self.phone_frame, text=f"Verification code sent to {self.phone_number}", font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(20, 5))
        
        self.code_entry = ctk.CTkEntry(self.phone_frame, placeholder_text="Code", width=300)
        self.code_entry.pack(pady=10)
        
        self.code_button = ctk.CTkButton(self.phone_frame, text="Verify Code", command=self.handle_code_entry)
        self.code_button.pack(pady=10)

        self.login_status_label = ctk.CTkLabel(self.phone_frame, text="")
        self.login_status_label.pack(pady=10)
        
        # We need to send the code request again since the client was just created.
        self.code_button.configure(state="disabled", text="Sending Code...")
        self.login_status_label.configure(text="Sending code...", text_color="yellow")
        executor.submit(self._run_async, send_phone_code(self, self.phone_number)).add_done_callback(self._handle_phone_code_result)

    def _handle_phone_code_result(self, future):
        """Handles the result of the code sending attempt."""
        result = future.result()
        if result == "code_sent":
            self.login_status_label.configure(text="Code sent successfully! Please enter it below.", text_color="green")
            self.code_button.configure(state="normal", text="Verify Code")
        else:
            self.login_status_label.configure(text=f"Error: {result}", text_color="red")
            self.code_button.configure(state="normal", text="Verify Code")
    
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
            widget.destroy()
        
        self.sent_count = 0  # Reset the count for the new session
        
        self.main_ui_frame = ctk.CTkFrame(self)
        self.main_ui_frame.pack(fill="both", expand=True)
        self.main_ui_frame.grid_columnconfigure(0, weight=1)
        self.main_ui_frame.grid_rowconfigure(5, weight=1)

        # Recreate the UI elements on the new frame
        self.msg_label = ctk.CTkLabel(self.main_ui_frame, text="Message to Send:")
        self.msg_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.msg_textbox = ctk.CTkTextbox(self.main_ui_frame, height=120)
        self.msg_textbox.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.info_frame = ctk.CTkFrame(self.main_ui_frame)
        self.info_frame.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="ew")
        self.info_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.groups_info = ctk.CTkLabel(self.info_frame, text="Groups: Loading...")
        self.groups_info.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        # Sent messages count label
        self.sent_count_label = ctk.CTkLabel(self.info_frame, text=f"Sent: {self.sent_count}")
        self.sent_count_label.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        self.delay_frame = ctk.CTkFrame(self.main_ui_frame)
        self.delay_frame.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="ew")
        self.delay_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.delay_label = ctk.CTkLabel(self.delay_frame, text="Delay (seconds):")
        self.delay_label.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.delay_entry = ctk.CTkEntry(self.delay_frame, textvariable=self.delay_var, width=100)
        self.delay_entry.grid(row=0, column=1, padx=10, pady=10, sticky="e")
        
        self.button_frame = ctk.CTkFrame(self.main_ui_frame)
        self.button_frame.grid(row=4, column=0, padx=20, pady=(10, 20), sticky="ew")
        self.button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        self.send_button = ctk.CTkButton(self.button_frame, text="🚀 Start Sending", command=self.start_sending, state="disabled")
        self.send_button.grid(row=0, column=0, padx=5, pady=10, sticky="ew")
        self.stop_button = ctk.CTkButton(self.button_frame, text="🛑 Stop Sending", command=self.stop_sending, state="disabled", fg_color="#d62828")
        self.stop_button.grid(row=0, column=1, padx=5, pady=10, sticky="ew")
        self.logout_button = ctk.CTkButton(self.button_frame, text="Logout", command=self.logout_user, fg_color="#5e5e5e")
        self.logout_button.grid(row=0, column=2, padx=5, pady=10, sticky="ew")

        self.log_label = ctk.CTkLabel(self.main_ui_frame, text="Activity Log:")
        self.log_label.grid(row=5, column=0, padx=20, pady=(0, 5), sticky="w")
        self.log_textbox = ctk.CTkTextbox(self.main_ui_frame, height=150)
        self.log_textbox.grid(row=6, column=0, padx=20, pady=(0, 20), sticky="nsew")
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
            is_connected = False
            try:
                is_connected = await client.is_connected()
            except TypeError:
                is_connected = client.is_connected()

            if client and is_connected:
                await client.log_out()
                return "success"
            else:
                return "not_connected"
        except Exception as e:
            # Fallback to manual removal if log_out fails
            return f"Error: {e}"
    
    def _handle_logout_complete(self, future):
        """Handles the result of the async logout operation."""
        try:
            result = future.result()
            if result == "success":
                self.log_to_textbox("Logout successful.")
            elif result == "not_connected":
                self.log_to_textbox("Client was not connected.")
            else:
                self.log_to_textbox(f"Logout failed: {result}")
        except Exception as e:
            self.log_to_textbox(f"An unexpected error occurred during logout: {e}")
        finally:
            self.after(0, self.show_account_selection_ui)

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
            
        # Reset sent count when a new process starts
        self.sent_count = 0
        self.sent_count_label.configure(text=f"Sent: {self.sent_count}")

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
