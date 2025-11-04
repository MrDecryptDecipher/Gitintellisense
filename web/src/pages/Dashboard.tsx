import React, { useState, useEffect } from 'react';
import { Row, Col, Card, Statistic, Progress, List, Tag, Typography, Space, Button } from 'antd';
import { 
  ReloadOutlined, 
  TrophyOutlined, 
  BugOutlined, 
  FileTextOutlined,
  CodeOutlined,
  ClockCircleOutlined 
} from '@ant-design/icons';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { apiService } from '../services/api';

const { Title, Text } = Typography;

interface DashboardStats {
  totalAnalyses: number;
  totalOpportunities: number;
  totalContributions: number;
  successRate: number;
  activeRepositories: number;
}

interface RecentActivity {
  id: string;
  type: 'analysis' | 'opportunity' | 'contribution';
  repository: string;
  description: string;
  timestamp: string;
  status: 'success' | 'pending' | 'failed';
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats>({
    totalAnalyses: 0,
    totalOpportunities: 0,
    totalContributions: 0,
    successRate: 0,
    activeRepositories: 0,
  });
  
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [loading, setLoading] = useState(true);
  const [chartData, setChartData] = useState<any[]>([]);

  useEffect(() => {
    loadDashboardData();
    
    // Set up real-time updates
    const interval = setInterval(loadDashboardData, 30000); // Update every 30 seconds
    
    return () => clearInterval(interval);
  }, []);

  const loadDashboardData = async () => {
    try {
      setLoading(true);
      
      // Load dashboard statistics
      const statsResponse = await apiService.getDashboardStats();
      setStats(statsResponse.data);
      
      // Load recent activity
      const activityResponse = await apiService.getRecentActivity();
      setRecentActivity(activityResponse.data);
      
      // Load chart data
      const chartResponse = await apiService.getAnalyticsData('7d');
      setChartData(chartResponse.data);
      
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'analysis':
        return <CodeOutlined style={{ color: '#1890ff' }} />;
      case 'opportunity':
        return <BugOutlined style={{ color: '#52c41a' }} />;
      case 'contribution':
        return <TrophyOutlined style={{ color: '#faad14' }} />;
      default:
        return <FileTextOutlined />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'success';
      case 'pending':
        return 'processing';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ color: '#ffffff', margin: 0 }}>
          Dashboard
        </Title>
        <Space>
          <div className="real-time-indicator">
            <div className="real-time-dot"></div>
            <Text style={{ color: '#8c8c8c' }}>Live Updates</Text>
          </div>
          <Button 
            icon={<ReloadOutlined />} 
            onClick={loadDashboardData}
            loading={loading}
          >
            Refresh
          </Button>
        </Space>
      </div>

      {/* Statistics Cards */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} lg={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Total Analyses"
              value={stats.totalAnalyses}
              prefix={<CodeOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Opportunities Found"
              value={stats.totalOpportunities}
              prefix={<BugOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Contributions Made"
              value={stats.totalContributions}
              prefix={<TrophyOutlined />}
              valueStyle={{ color: '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card className="dashboard-card">
            <Statistic
              title="Success Rate"
              value={stats.successRate}
              suffix="%"
              valueStyle={{ color: stats.successRate > 80 ? '#52c41a' : '#faad14' }}
            />
            <Progress 
              percent={stats.successRate} 
              showInfo={false} 
              strokeColor={stats.successRate > 80 ? '#52c41a' : '#faad14'}
              style={{ marginTop: 8 }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        {/* Activity Chart */}
        <Col xs={24} lg={16}>
          <Card 
            title="Activity Trends (Last 7 Days)" 
            className="dashboard-card"
            extra={<ClockCircleOutlined />}
          >
            <div className="chart-container">
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#434343" />
                  <XAxis dataKey="date" stroke="#8c8c8c" />
                  <YAxis stroke="#8c8c8c" />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1f1f1f', 
                      border: '1px solid #434343',
                      color: '#ffffff'
                    }} 
                  />
                  <Line 
                    type="monotone" 
                    dataKey="analyses" 
                    stroke="#1890ff" 
                    strokeWidth={2}
                    name="Analyses"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="opportunities" 
                    stroke="#52c41a" 
                    strokeWidth={2}
                    name="Opportunities"
                  />
                  <Line 
                    type="monotone" 
                    dataKey="contributions" 
                    stroke="#faad14" 
                    strokeWidth={2}
                    name="Contributions"
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </Col>

        {/* Recent Activity */}
        <Col xs={24} lg={8}>
          <Card 
            title="Recent Activity" 
            className="dashboard-card"
            extra={<Text style={{ color: '#8c8c8c' }}>Last 24 hours</Text>}
          >
            <List
              dataSource={recentActivity}
              renderItem={(item) => (
                <List.Item style={{ border: 'none', padding: '8px 0' }}>
                  <List.Item.Meta
                    avatar={getActivityIcon(item.type)}
                    title={
                      <Space>
                        <Text style={{ color: '#ffffff' }}>{item.repository}</Text>
                        <Tag color={getStatusColor(item.status)}>{item.status}</Tag>
                      </Space>
                    }
                    description={
                      <div>
                        <Text style={{ color: '#8c8c8c' }}>{item.description}</Text>
                        <br />
                        <Text style={{ color: '#595959', fontSize: '12px' }}>
                          {new Date(item.timestamp).toLocaleString()}
                        </Text>
                      </div>
                    }
                  />
                </List.Item>
              )}
              locale={{ emptyText: 'No recent activity' }}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
