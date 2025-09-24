import customtkinter as ctk
import os
from src.services.account_service import load_accounts, save_accounts
from src.config.settings import SESSION_FILE_PREFIX
from src.utils.async_runner import executor, run_async
from src.services.telegram_service import TelegramService

class App(ctk.CTk):
    def __init__(self, loop):
        super().__init__()

        self.title("Telegram Group Sender")
        self.geometry("400x450")

        self.groups_data = []
        self.delay_var = ctk.StringVar(value="60")
        self.phone_number = None
        self.accounts = load_accounts()
        self.sent_count = 0
        
        self.telegram_service = TelegramService(loop)

        self.show_account_selection_ui()
        
    def show_account_selection_ui(self):
        for widget in self.winfo_children():
            widget.destroy()

        self.account_frame = ctk.CTkFrame(self)
        self.account_frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(self.account_frame, text="Select an Account", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(20, 10))
        
        self.account_list_frame = ctk.CTkScrollableFrame(self.account_frame)
        self.account_list_frame.pack(fill="both", expand=True, padx=10, pady=10)

        self.update_account_list()
        
        ctk.CTkButton(self.account_frame, text="Add New Account", command=self.show_add_account_ui).pack(pady=10)
        ctk.CTkLabel(self.account_frame, text="Log:").pack(pady=(10, 5))
        self.status_label = ctk.CTkLabel(self.account_frame, text="Add a new account or select an existing one.")
        self.status_label.pack(pady=5)
        
    def update_account_list(self):
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
        if phone in self.accounts:
            del self.accounts[phone]
            save_accounts(self.accounts)
            
            session_file = f"{SESSION_FILE_PREFIX}{phone}.session"
            if os.path.exists(session_file):
                os.remove(session_file)
            
            self.status_label.configure(text=f"Account {phone} deleted.")
            self.update_account_list()

    def show_add_account_ui(self):
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
        if hasattr(self, 'log_textbox'):
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", text + "\n")
            self.log_textbox.see("end")
            self.log_textbox.configure(state="disabled")

    def increment_sent_count(self):
        self.sent_count += 1
        if hasattr(self, 'sent_count_label'):
            self.sent_count_label.configure(text=f"Sent: {self.sent_count}")

    def attempt_login(self, phone_number, details):
        self.phone_number = phone_number
        self.status_label.configure(text=f"Connecting to {self.phone_number}...", text_color="yellow")
        executor.submit(run_async, self._attempt_login_async(details['api_id'], details['api_hash'], phone_number)).add_done_callback(self._handle_login_result)

    async def _attempt_login_async(self, api_id, api_hash, phone_number):
        try:
            if self.telegram_service.client:
                await self.telegram_service.disconnect()
            await self.telegram_service.connect(api_id, api_hash, phone_number)
            if await self.telegram_service.is_user_authorized():
                return "authorized"
            else:
                return "phone_required"
        except Exception as e:
            return f"Error: {e}"

    def _handle_login_result(self, future):
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
        
        self.code_button.configure(state="disabled", text="Sending Code...")
        self.login_status_label.configure(text="Sending code...", text_color="yellow")
        executor.submit(run_async, self.telegram_service.send_code_request(self.phone_number)).add_done_callback(self._handle_phone_code_result)

    def _handle_phone_code_result(self, future):
        try:
            future.result()
            self.login_status_label.configure(text="Code sent successfully! Please enter it below.", text_color="green")
            self.code_button.configure(state="normal", text="Verify Code")
        except Exception as e:
            self.login_status_label.configure(text=f"Error: {e}", text_color="red")
            self.code_button.configure(state="normal", text="Verify Code")
    
    def handle_code_entry(self):
        phone_code = self.code_entry.get().strip()
        if not phone_code:
            self.login_status_label.configure(text="Please enter the code.", text_color="red")
            return
        
        self.code_button.configure(state="disabled", text="Verifying...")
        self.login_status_label.configure(text="Verifying...", text_color="yellow")
        executor.submit(run_async, self.telegram_service.sign_in(self.phone_number, phone_code)).add_done_callback(self._handle_code_verification_result)
        
    def _handle_code_verification_result(self, future):
        try:
            future.result()
            self.login_status_label.configure(text="Login successful!", text_color="green")
            self.after(100, self.show_main_ui)
        except Exception as e:
            self.login_status_label.configure(text=f"Login failed: {e}", text_color="red")
            self.code_button.configure(state="normal", text="Verify Code")
    
    def show_main_ui(self):
        for widget in self.winfo_children():
            widget.destroy()
        
        self.sent_count = 0
        
        self.main_ui_frame = ctk.CTkFrame(self)
        self.main_ui_frame.pack(fill="both", expand=True)
        self.main_ui_frame.grid_columnconfigure(0, weight=1)
        self.main_ui_frame.grid_rowconfigure(5, weight=1)

        self.msg_label = ctk.CTkLabel(self.main_ui_frame, text="Message to Send:")
        self.msg_label.grid(row=0, column=0, padx=20, pady=(20, 5), sticky="w")
        self.msg_textbox = ctk.CTkTextbox(self.main_ui_frame, height=120)
        self.msg_textbox.grid(row=1, column=0, padx=20, pady=5, sticky="ew")

        self.info_frame = ctk.CTkFrame(self.main_ui_frame)
        self.info_frame.grid(row=2, column=0, padx=20, pady=(10, 10), sticky="ew")
        self.info_frame.grid_columnconfigure((0, 1), weight=1)
        
        self.groups_info = ctk.CTkLabel(self.info_frame, text="Groups: Loading...")
        self.groups_info.grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
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
        self.log_to_textbox("Logging out...")
        executor.submit(run_async, self.telegram_service.logout()).add_done_callback(self._handle_logout_complete)

    def _handle_logout_complete(self, future):
        try:
            future.result()
            self.log_to_textbox("Logout successful.")
        except Exception as e:
            self.log_to_textbox(f"Logout failed: {e}")
        finally:
            self.after(0, self.show_account_selection_ui)

    def load_groups(self):
        self.groups_info.configure(text="Groups: Fetching...")
        self.log_to_textbox("Connecting to Telegram and fetching groups...")
        executor.submit(run_async, self.telegram_service.get_groups()).add_done_callback(self._groups_loaded_callback)

    def _groups_loaded_callback(self, future):
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
            
        self.sent_count = 0
        self.sent_count_label.configure(text=f"Sent: {self.sent_count}")

        self.send_button.configure(state="disabled", text="Sending...")
        self.stop_button.configure(state="normal")
        self.log_to_textbox(f"\n--- Starting sending process (Delay: {delay}s) ---")
        
        log_cb = lambda msg: self.after(0, self.log_to_textbox, msg)
        prog_cb = lambda: self.after(0, self.increment_sent_count)

        executor.submit(
            run_async,
            self.telegram_service.send_message_to_groups(message, delay, self.groups_data, log_cb, prog_cb)
        ).add_done_callback(self._sending_finished_callback)

    def stop_sending(self):
        self.telegram_service.request_stop()
        self.stop_button.configure(state="disabled", text="Stopping...")
        self.send_button.configure(state="disabled")

    def _sending_finished_callback(self, future):
        self.send_button.configure(state="normal", text="🚀 Start Sending")
        self.stop_button.configure(state="disabled", text="🛑 Stop Sending")
        
        if future.exception():
            self.log_to_textbox(f"❌ Critical Error during sending: {future.exception()}")
