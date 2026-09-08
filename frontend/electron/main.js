const { app, BrowserWindow, globalShortcut, ipcMain, desktopCapturer, screen } = require('electron');
const path = require('path');

let popupWindow = null;

function createPopupWindow() {
  const { width } = screen.getPrimaryDisplay().workAreaSize;
  
  popupWindow = new BrowserWindow({
    title: 'MedDeck',
    width: 500,
    height: 600,
    x: width - 520,
    y: 50,
    show: false,
    frame: true,
    transparent: false,
    alwaysOnTop: true,
    resizable: true,
    backgroundColor: '#1e1e1e',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  popupWindow.loadFile(path.join(__dirname, '..', 'src', 'index.html'));
  // popupWindow.webContents.openDevTools({ mode: 'detach' });
  
  popupWindow.on('closed', () => {
    popupWindow = null;
  });
}

async function captureScreen() {
  const { width, height } = screen.getPrimaryDisplay().size;
  const sources = await desktopCapturer.getSources({
    types: ['screen'],
    thumbnailSize: { width, height }
  });
  
  const primaryScreen = sources[0];
  const base64 = primaryScreen.thumbnail.toPNG().toString('base64');
  return base64;
}

app.whenReady().then(() => {
  createPopupWindow();
  
  const ret = globalShortcut.register('CommandOrControl+Shift+G', async () => {
    console.log('Hotkey pressed!');
    
    if (!popupWindow) {
      createPopupWindow();
    }
    
    // Hide window first so it doesn't appear in the screenshot
    if (popupWindow.isVisible()) {
      popupWindow.hide();
    }
    
    // Give macOS a moment to actually hide the window
    await new Promise(resolve => setTimeout(resolve, 200));
    
    try {
      const screenshot = await captureScreen();
      popupWindow.show();
      popupWindow.focus();
      popupWindow.webContents.send('screenshot-captured', screenshot);
    } catch (err) {
      console.error('Screenshot failed:', err);
      popupWindow.show();
    }
  });
  
  console.log('Shortcut registered:', ret);
});

ipcMain.handle('generate-card', async (event, { imageBase64, reason }) => {
  try {
    const response = await fetch('http://127.0.0.1:8001/generate-card', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        image_base64: imageBase64
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Backend error: ${errorText}`);
    }
    
    return await response.json();
  } catch (err) {
    return { error: err.message };
  }
});

ipcMain.handle('save-card', async (event, { front, back, reason, deckName }) => {
  try {
    const response = await fetch('http://127.0.0.1:8001/save-card', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        anki_front: front,
        anki_back: back,
        reason: reason,
        deck_name: deckName || 'Wrong Answers'
      })
    });
    
    if (!response.ok) {
      const errorText = await response.text();
      throw new Error(`Backend error: ${errorText}`);
    }
    
    return await response.json();
  } catch (err) {
    return { error: err.message };
  }
});

ipcMain.handle('list-decks', async () => {
  try {
    const response = await fetch('http://127.0.0.1:8001/decks');
    if (!response.ok) throw new Error('Failed to fetch decks');
    return await response.json();
  } catch (err) {
    return { error: err.message };
  }
});

ipcMain.handle('create-deck', async (event, { deckName }) => {
  try {
    const response = await fetch('http://127.0.0.1:8001/decks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ deck_name: deckName })
    });
    if (!response.ok) throw new Error('Failed to create deck');
    return await response.json();
  } catch (err) {
    return { error: err.message };
  }
});

ipcMain.on('hide-popup', () => {
  if (popupWindow) popupWindow.hide();
});

app.on('window-all-closed', (e) => {
  e.preventDefault();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});