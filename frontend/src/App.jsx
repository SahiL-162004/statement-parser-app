import React, { useState } from 'react';

// --- STYLES OBJECT ---
const styles = {
  page: {
    minHeight: '100vh',
    backgroundColor: '#f0f2f5',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: '40px 20px',
    boxSizing: 'border-box',
  },
  header: {
    textAlign: 'center',
    marginBottom: '40px',
  },
  h1: {
    fontSize: '2.25rem',
    fontWeight: 'bold',
    color: '#1f2937',
  },
  p: {
    fontSize: '1.125rem',
    color: '#6b7280',
    marginTop: '8px',
  },
  card: {
    width: '100%',
    maxWidth: '800px',
    backgroundColor: '#ffffff',
    padding: '24px',
    borderRadius: '8px',
    boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)',
    marginTop: '24px',
  },
  fileInputContainer: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '16px',
  },
  fileInputLabel: {
    padding: '10px 20px',
    backgroundColor: '#f3f4f6',
    color: '#374151',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '600',
    border: '1px solid #d1d5db',
  },
  buttonContainer: {
    display: 'flex',
    gap: '16px',
    marginTop: '24px',
  },
  button: {
    padding: '12px 24px',
    border: 'none',
    borderRadius: '6px',
    fontWeight: '600',
    color: 'white',
    cursor: 'pointer',
  },
  primaryButton: { backgroundColor: '#3b82f6' },
  secondaryButton: { backgroundColor: '#4b5563' },
  disabledButton: { backgroundColor: '#9ca3af', cursor: 'not-allowed' },
  message: {
    marginTop: '16px',
    padding: '8px',
    borderRadius: '4px',
    fontWeight: '500',
  },
  successMessage: { backgroundColor: '#d1fae5', color: '#065f46' },
  errorMessage: { backgroundColor: '#fee2e2', color: '#991b1b' },
  pre: {
    backgroundColor: '#f9fafb',
    padding: '16px',
    borderRadius: '6px',
    overflowX: 'auto',
    textAlign: 'left',
  },
  chatBox: {
    height: '250px',
    overflowY: 'auto',
    border: '1px solid #e5e7eb',
    borderRadius: '6px',
    padding: '12px',
    marginBottom: '16px',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  chatBubble: {
    padding: '8px 12px',
    borderRadius: '12px',
    maxWidth: '75%',
  },
  userBubble: {
    backgroundColor: '#3b82f6',
    color: 'white',
    alignSelf: 'flex-end',
  },
  botBubble: {
    backgroundColor: '#e5e7eb',
    color: '#1f2937',
    alignSelf: 'flex-start',
  },
  chatInputContainer: {
    display: 'flex',
    gap: '8px',
  },
  chatInput: {
    flexGrow: 1,
    padding: '10px',
    border: '1px solid #d1d5db',
    borderRadius: '6px',
  },
  downloadBtn: {
    marginTop: '16px',
    padding: '10px 20px',
    backgroundColor: '#10b981',
    color: 'white',
    border: 'none',
    borderRadius: '6px',
    cursor: 'pointer',
    fontWeight: '600',
  }
};

const ResultsCard = ({ data }) => {
  // --- Download JSON handler ---
  const handleDownload = () => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'parsed_results.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div style={styles.card}>
      <h2 style={{...styles.h1, fontSize: '1.5rem', marginBottom: '16px' }}>Parsed Results</h2>
      <pre style={styles.pre}>{JSON.stringify(data, null, 2)}</pre>
      <button onClick={handleDownload} style={styles.downloadBtn}>⬇️ Download JSON</button>
    </div>
  );
};

const ChatCard = ({ sessionId }) => {
  const [prompt, setPrompt] = useState('');
  const [messages, setMessages] = useState([]);
  const [isChatLoading, setIsChatLoading] = useState(false);

  const handleSend = async () => {
    if (!prompt || isChatLoading) return;
    setIsChatLoading(true);
    const newMessages = [...messages, { sender: 'user', text: prompt }];
    setMessages(newMessages);
    setPrompt('');
    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, prompt })
      });
      const result = await response.json();
      setMessages([...newMessages, { sender: 'bot', text: result.response }]);
    } catch (error) {
      setMessages([...newMessages, { sender: 'bot', text: 'Error communicating with the chat server.' }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  return (
    <div style={styles.card}>
      <h2 style={{...styles.h1, fontSize: '1.5rem', marginBottom: '16px' }}>Chat with your Document</h2>
      <div style={styles.chatBox}>
        {messages.map((msg, index) => (
          <div key={index} style={{ ...styles.chatBubble, ...(msg.sender === 'user' ? styles.userBubble : styles.botBubble) }}>
            {msg.text.split('\n').map((line, i) => <p key={i}>{line}</p>)}
          </div>
        ))}
      </div>
      <div style={styles.chatInputContainer}>
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Ask a question..."
          style={styles.chatInput}
        />
        <button onClick={handleSend} disabled={isChatLoading} style={{...styles.button, ...styles.primaryButton, ...(isChatLoading && styles.disabledButton)}}>
          Send
        </button>
      </div>
    </div>
  );
};

function App() {
  const [selectedFile, setSelectedFile] = useState(null);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [parsedData, setParsedData] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState(null);

  const handleFileChange = (event) => {
    setSelectedFile(event.target.files[0]);
    setMessage({ text: '', type: '' });
    setParsedData(null);
    setSessionId(null);
  };

  const handleUpload = async (endpoint, type) => {
    if (!selectedFile) {
      setMessage({ text: 'Please select a file first.', type: 'error' });
      return;
    }
    setIsLoading(true);
    setParsedData(null);
    setSessionId(null);
    setMessage({ text: `Analyzing with ${type}...`, type: 'info' });
    const formData = new FormData();
    formData.append('file', selectedFile);
    try {
      const response = await fetch(`http://localhost:8000${endpoint}`, { method: 'POST', body: formData });
      const result = await response.json();
      if (result.status === 'success') {
        setMessage({ text: 'File parsed successfully!', type: 'success' });
        setParsedData(result.data);
        setSessionId(result.session_id);
      } else {
        throw new Error(result.message);
      }
    } catch (error) {
      setMessage({ text: `Error: ${error.message}`, type: 'error' });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.header}>
        <h1 style={styles.h1}>Smart Statement Analyzer</h1>
        <p style={styles.p}>Upload, Analyze, and Chat with your financial documents.</p>
      </div>

      <div style={styles.card}>
        <div style={styles.fileInputContainer}>
          <label htmlFor="file-upload" style={styles.fileInputLabel}>
            Choose a PDF File
          </label>
          <input id="file-upload" type="file" accept=".pdf" onChange={handleFileChange} style={{ display: 'none' }} />
          {selectedFile && <p style={{ fontWeight: '600', color: '#3b82f6' }}>Selected: {selectedFile.name}</p>}
        </div>
        <div style={styles.buttonContainer}>
          <button onClick={() => handleUpload('/api/upload-pdf', 'Rules')} disabled={isLoading || !selectedFile} style={{...styles.button, ...styles.secondaryButton, ...((isLoading || !selectedFile) && styles.disabledButton)}}>
            {isLoading ? 'Analyzing...' : 'Analyze with Rules'}
          </button>
          <button onClick={() => handleUpload('/api/upload-ml', 'AI')} disabled={isLoading || !selectedFile} style={{...styles.button, ...styles.primaryButton, ...((isLoading || !selectedFile) && styles.disabledButton)}}>
            {isLoading ? 'Analyzing...' : 'Analyze with AI'}
          </button>
        </div>
        {message.text && (
          <p style={{...styles.message, ...(message.type === 'success' ? styles.successMessage : styles.errorMessage)}}>
            {message.text}
          </p>
        )}
      </div>

      {parsedData && <ResultsCard data={parsedData} />}
      {sessionId && <ChatCard sessionId={sessionId} />}
    </div>
  );
}

export default App;
