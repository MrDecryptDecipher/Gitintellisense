import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout, ConfigProvider, theme } from 'antd';
import Sidebar from './components/Sidebar';
import Dashboard from './pages/Dashboard';
import RepositoryAnalysis from './pages/RepositoryAnalysis';
import Opportunities from './pages/Opportunities';
import PRGeneration from './pages/PRGeneration';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';
import './App.css';

const { Content } = Layout;

const App: React.FC = () => {
  return (
    <ConfigProvider
      theme={{
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#1890ff',
        },
      }}
    >
      <Router>
        <Layout style={{ minHeight: '100vh' }}>
          <Sidebar />
          <Layout>
            <Content style={{ margin: '24px 16px', padding: 24, background: '#001529' }}>
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/analysis" element={<RepositoryAnalysis />} />
                <Route path="/opportunities" element={<Opportunities />} />
                <Route path="/pr-generation" element={<PRGeneration />} />
                <Route path="/analytics" element={<Analytics />} />
                <Route path="/settings" element={<Settings />} />
              </Routes>
            </Content>
          </Layout>
        </Layout>
      </Router>
    </ConfigProvider>
  );
};

export default App;
