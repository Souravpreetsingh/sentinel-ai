import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import Layout from './components/layout/Layout';
import CommandCenter from './pages/CommandCenter';
import Cameras from './pages/Cameras';
import CameraDetail from './pages/CameraDetail';
import Incidents from './pages/Incidents';
import CityMap from './pages/CityMap';
import Analytics from './pages/Analytics';
import Assistant from './pages/Assistant';
import Evidence from './pages/Evidence';
import SystemHealth from './pages/SystemHealth';
import Settings from './pages/Settings';
import NotFound from './pages/NotFound';
import Watchlists from './pages/Watchlists';
import Alerts from './pages/Alerts';
import Investigation from './pages/Investigation';
import LiveWall from './pages/LiveWall';

export default function App() {
  return (
    <AppProvider>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<CommandCenter />} />
            <Route path="/cameras" element={<Cameras />} />
            <Route path="/cameras/:id" element={<CameraDetail />} />
            <Route path="/incidents" element={<Incidents />} />
            <Route path="/incidents/:id" element={<Incidents />} />
            <Route path="/map" element={<CityMap />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/assistant" element={<Assistant />} />
            <Route path="/evidence" element={<Evidence />} />
            <Route path="/system" element={<SystemHealth />} />
            <Route path="/watchlists" element={<Watchlists />} />
            <Route path="/alerts" element={<Alerts />} />
            <Route path="/investigation" element={<Investigation />} />
            <Route path="/live-wall" element={<LiveWall />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </AppProvider>
  );
}
