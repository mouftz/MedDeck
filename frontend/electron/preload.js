const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('api', {
  onScreenshot: (callback) => {
    ipcRenderer.on('screenshot-captured', (event, base64) => callback(base64));
  },
  generateCard: (imageBase64, reason) => {
    return ipcRenderer.invoke('generate-card', { imageBase64, reason });
  },
  saveCard: (front, back, reason, deckName) => {
    return ipcRenderer.invoke('save-card', { front, back, reason, deckName });
  },
  listDecks: () => {
    return ipcRenderer.invoke('list-decks');
  },
  createDeck: (deckName) => {
    return ipcRenderer.invoke('create-deck', { deckName });
  },
  hidePopup: () => {
    ipcRenderer.send('hide-popup');
  }
});