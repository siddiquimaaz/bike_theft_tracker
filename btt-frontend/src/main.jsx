import ReactDOM from 'react-dom/client';
import App from './app/App';
import './shared/styles/index.css';

// React.StrictMode intentionally double-invokes effects in development to
// surface side effects — this caused every tab navigation to hit each API
// endpoint twice. Removed for demo clarity; re-enable if needed for debugging.
ReactDOM.createRoot(document.getElementById('root')).render(<App />);
