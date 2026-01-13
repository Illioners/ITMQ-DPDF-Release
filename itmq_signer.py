import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import subprocess
import os

class ITMQSignerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("ITMQ Digital Signer")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # Styles
        style = ttk.Style()
        style.configure("TButton", padding=5)
        
        # Main Frame
        main_frame = ttk.Frame(root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Firma Digital ITMQ", font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # EXE Selection
        ttk.Label(main_frame, text="Archivo Ejecutable (.exe):").pack(anchor=tk.W)
        exe_frame = ttk.Frame(main_frame)
        exe_frame.pack(fill=tk.X, pady=(0, 10))
        self.exe_path = tk.StringVar()
        ttk.Entry(exe_frame, textvariable=self.exe_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(exe_frame, text="...", width=3, command=self.browse_exe).pack(side=tk.LEFT, padx=(5, 0))
        
        # PFX Selection
        ttk.Label(main_frame, text="Certificado (.pfx):").pack(anchor=tk.W)
        pfx_frame = ttk.Frame(main_frame)
        pfx_frame.pack(fill=tk.X, pady=(0, 10))
        self.pfx_path = tk.StringVar()
        ttk.Entry(pfx_frame, textvariable=self.pfx_path).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(pfx_frame, text="...", width=3, command=self.browse_pfx).pack(side=tk.LEFT, padx=(5, 0))
        
        # Password
        ttk.Label(main_frame, text="Contraseña:").pack(anchor=tk.W)
        self.password = tk.StringVar()
        self.pass_entry = ttk.Entry(main_frame, textvariable=self.password, show="*")
        self.pass_entry.pack(fill=tk.X, pady=(0, 20))
        
        # Sign Button
        self.sign_btn = ttk.Button(main_frame, text="FIRMAR AHORA", command=self.sign_file)
        self.sign_btn.pack(pady=10)
        
        # Log Area
        self.log_text = tk.Text(main_frame, height=4, state=tk.DISABLED, font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def browse_exe(self):
        path = filedialog.askopenfilename(filetypes=[("Ejecutable", "*.exe")])
        if path: self.exe_path.set(path)
        
    def browse_pfx(self):
        path = filedialog.askopenfilename(filetypes=[("Certificado PFX", "*.pfx")])
        if path: self.pfx_path.set(path)
        
    def log(self, message):
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, message)
        self.log_text.config(state=tk.DISABLED)

    def sign_file(self):
        exe = self.exe_path.get()
        pfx = self.pfx_path.get()
        pwd = self.password.get()
        
        if not exe or not pfx or not pwd:
            messagebox.showerror("Error", "Todos los campos son obligatorios.")
            return
            
        if not os.path.exists(exe) or not os.path.exists(pfx):
            messagebox.showerror("Error", "Archivo no encontrado.")
            return

        self.sign_btn.config(state=tk.DISABLED)
        self.log("Procesando...")
        self.root.update()
        
        # PowerShell command
        ps_command = f'''
        try {{
            $cert = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2("{pfx}", "{pwd}")
            Set-AuthenticodeSignature -FilePath "{exe}" -Certificate $cert
            exit 0
        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
        '''
        
        try:
            result = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-NonInteractive", "-Command", ps_command], capture_output=True, text=True)
            
            if result.returncode == 0:
                self.log("ÉXITO: El archivo ha sido firmado.")
                messagebox.showinfo("Éxito", "Firma digital aplicada correctamente.")
            else:
                error_msg = result.stderr if result.stderr else "Error desconocido."
                self.log(f"ERROR: {error_msg}")
                messagebox.showerror("Error de Firma", f"No se pudo firmar el archivo.\n\n{error_msg}")
        except Exception as e:
            self.log(f"Excepción: {str(e)}")
            messagebox.showerror("Error Fatal", str(e))
        finally:
            self.sign_btn.config(state=tk.NORMAL)

if __name__ == "__main__":
    root = tk.Tk()
    app = ITMQSignerApp(root)
    root.mainloop()
