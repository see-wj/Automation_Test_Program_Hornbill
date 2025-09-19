# Python Test Automation Program

This is the remote repository for the automation test program used for Excavator, Hornbill and future DUT. 

## 📖 Getting Started

The program was developed using PyQt5 integrated with PyVisa Module to control the instrument via SCPI command.


## 🖥 For Non-Technical Users
You don’t need Python or VS Code!  
You can download the latest `.exe` build from **[GitHub Releases](https://github.com/ztian914/Automation_Test_Program/releases/)** and run it directly.

## 📚 User Guide

To access the **User Guide** (hosted on the company network):

**Path:**  
`file://remus/BID_RnD/Excavator/Zhuo_Tian_Test_Program/Internship_Documentation_ZhuoTian/`  

> 💡 Make sure you are connected to the **company Wi-Fi** and have mapped the network drive.  
> Then, copy the path above and paste it into **Microsoft Edge** to open the guide.
> Else, you can get the documentation from **Wei Jing**


## 📦Getting Started
Follow these steps to set up and run the application

### 1. Requirements
- **Python** `>= 3.11.2`  
  Download from the [official Python website](https://www.python.org/downloads/).
- **Visual Studio Code**  
  Download from the [VS Code website](https://code.visualstudio.com/).  
  Install the [Python extension](https://marketplace.visualstudio.com/items?itemName=ms-python.python).

---
### 2. Create and Activate a Virtual Environment in VS Code (Recommended) 
Using a virtual environment keeps dependencies isolated from other projects.

1. Open your project folder in **VS Code**.
2. Open the integrated terminal (**Ctrl + `**).
3. Create the virtual environment:
    ```cmd
   python -m venv .venv
    ```
4. In VS Code, press **Ctrl + Shift + P**, search for **Python: Select Interpreter**,  
   and choose the one from `.venv`.
5. Close the terminal and open a new one — VS Code should automatically activate the venv.  
   You’ll know it’s active if your terminal prompt shows:
   ```
   (.venv) path\to\project>
   ```
---
### 3.   Install Dependencies
The dependencies for this program has been listed in `requirements.txt`. If you are running a virtual environment, you can install the dependencies using:

```cmd
pip install -r requirements.txt
```

If requirements.txt does not exist
Install the following manually:

```cmd
pip install PyVISA==1.14.1
pip install matplotlib==3.10.5
pip install numpy==2.3.2
pip install openpyxl==3.1.5
pip install pandas==2.3.1
pip install Pillow==11.3.0
pip install PyQt5==5.15.11
pip install PyQt5_sip==12.17.0

```
---

### 4. Run the Application
Inside the activated virtual environment, run:

```cmd
python GUI.py
```

---

## 🔄 Git Integration
This project uses Git for version control.

- To clone the repository:

```cmd
git clone https://github.com/ztian914/Automation_Test_Program.git
```

- To pull the latest updates:

```cmd
git pull
```

**For better understanding on the use of git, you can refer to the user guide slide.**

---
## ⚙ Build Information
- The `.exe` file is **automatically built** using **GitHub Actions** whenever changes are pushed to the `master` branch, and uploaded to **GitHub Releases**.
- If you want to build it manually, you can use the included `Make_GUI_Executable_Program.py` build script:

```cmd
python Make_GUI_Executable_Program.py
```

The generated `.exe` will be inside the `src` folder.

---
## 👤 Authors

Contributors names and contact info
- Zhi Yuan Wong

- Lim Zhuo Tian
[@ZhuoTian](https://www.linkedin.com/in/lim-zhuo-tian-1741342b4)

- Wei Jing See

---

## 📌 Others
- This project has no license, but it is confidential under the use of **Keysight Technologies**. 
- Contributions, suggestions, and bug reports are welcome.
- Good luck for reading the code for the next developers.

---


