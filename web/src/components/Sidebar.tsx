import React, { useState } from 'react';
import { Layout, Menu, Typography } from 'antd';
import {
  DashboardOutlined,
  SearchOutlined,
  BulbOutlined,
  CodeOutlined,
  BarChartOutlined,
  SettingOutlined,
  GithubOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Sider } = Layout;
const { Title } = Typography;

const Sidebar: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    {
      key: '/',
      icon: <DashboardOutlined />,
      label: 'Dashboard',
    },
    {
      key: '/analysis',
      icon: <SearchOutlined />,
      label: 'Repository Analysis',
    },
    {
      key: '/opportunities',
      icon: <BulbOutlined />,
      label: 'Opportunities',
    },
    {
      key: '/pr-generation',
      icon: <CodeOutlined />,
      label: 'PR Generation',
    },
    {
      key: '/analytics',
      icon: <BarChartOutlined />,
      label: 'Analytics',
    },
    {
      key: '/settings',
      icon: <SettingOutlined />,
      label: 'Settings',
    },
  ];

  const handleMenuClick = (e: any) => {
    navigate(e.key);
  };

  return (
    <Sider
      collapsible
      collapsed={collapsed}
      onCollapse={(value) => setCollapsed(value)}
      theme="dark"
      width={250}
    >
      <div style={{ padding: '16px', textAlign: 'center' }}>
        <GithubOutlined style={{ fontSize: '24px', color: '#1890ff', marginBottom: '8px' }} />
        {!collapsed && (
          <Title level={4} style={{ color: '#ffffff', margin: 0 }}>
            GitIntellisense
          </Title>
        )}
      </div>
      
      <Menu
        theme="dark"
        selectedKeys={[location.pathname]}
        mode="inline"
        items={menuItems}
        onClick={handleMenuClick}
        style={{ borderRight: 0 }}
      />
    </Sider>
  );
};

export default Sidebar;
