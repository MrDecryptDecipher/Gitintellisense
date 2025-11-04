import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Input, 
  Button, 
  Table, 
  Tag, 
  Progress, 
  Space, 
  Typography, 
  Modal,
  Descriptions,
  Alert,
  message
} from 'antd';
import { 
  SearchOutlined, 
  ReloadOutlined, 
  EyeOutlined,
  TrophyOutlined,
  BugOutlined,
  FileTextOutlined
} from '@ant-design/icons';
import { apiService, RepositoryAnalysis } from '../services/api';

const { Title, Text } = Typography;
const { Search } = Input;

const RepositoryAnalysisPage: React.FC = () => {
  const [analyses, setAnalyses] = useState<RepositoryAnalysis[]>([]);
  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [selectedAnalysis, setSelectedAnalysis] = useState<RepositoryAnalysis | null>(null);
  const [detailsVisible, setDetailsVisible] = useState(false);

  useEffect(() => {
    loadAnalyses();
  }, []);

  const loadAnalyses = async () => {
    try {
      setLoading(true);
      const response = await apiService.getRepositoryAnalyses(100);
      setAnalyses(response.data);
    } catch (error) {
      message.error('Failed to load repository analyses');
      console.error('Failed to load analyses:', error);
    } finally {
      setLoading(false);
    }
  };

  const analyzeRepository = async (repository: string) => {
    try {
      setAnalyzing(true);
      await apiService.analyzeRepository(repository);
      message.success(`Analysis started for ${repository}`);
      
      // Reload analyses after a short delay
      setTimeout(loadAnalyses, 2000);
    } catch (error) {
      message.error('Failed to start repository analysis');
      console.error('Failed to analyze repository:', error);
    } finally {
      setAnalyzing(false);
    }
  };

  const showDetails = (analysis: RepositoryAnalysis) => {
    setSelectedAnalysis(analysis);
    setDetailsVisible(true);
  };

  const getHealthScoreColor = (score: number) => {
    if (score >= 80) return '#52c41a';
    if (score >= 60) return '#faad14';
    return '#ff4d4f';
  };

  const getActivityLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'very_active':
        return 'green';
      case 'active':
        return 'blue';
      case 'moderate':
        return 'orange';
      case 'low':
        return 'red';
      default:
        return 'default';
    }
  };

  const getDifficultyColor = (difficulty: string) => {
    switch (difficulty.toLowerCase()) {
      case 'easy':
        return 'green';
      case 'medium':
        return 'orange';
      case 'hard':
        return 'red';
      default:
        return 'default';
    }
  };

  const columns = [
    {
      title: 'Repository',
      dataIndex: 'repository',
      key: 'repository',
      render: (text: string) => (
        <Text strong style={{ color: '#1890ff' }}>{text}</Text>
      ),
    },
    {
      title: 'Health Score',
      dataIndex: 'health_score',
      key: 'health_score',
      render: (score: number) => (
        <div style={{ width: 120 }}>
          <Progress
            percent={score}
            size="small"
            strokeColor={getHealthScoreColor(score)}
            format={(percent) => `${percent}/100`}
          />
        </div>
      ),
      sorter: (a: RepositoryAnalysis, b: RepositoryAnalysis) => a.health_score - b.health_score,
    },
    {
      title: 'Activity Level',
      dataIndex: 'activity_level',
      key: 'activity_level',
      render: (level: string) => (
        <Tag color={getActivityLevelColor(level)}>
          {level.replace('_', ' ').toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Difficulty',
      dataIndex: 'contribution_difficulty',
      key: 'contribution_difficulty',
      render: (difficulty: string) => (
        <Tag color={getDifficultyColor(difficulty)}>
          {difficulty.toUpperCase()}
        </Tag>
      ),
    },
    {
      title: 'Good First Issues',
      dataIndex: 'good_first_issues',
      key: 'good_first_issues',
      render: (count: number) => (
        <Space>
          <BugOutlined style={{ color: '#52c41a' }} />
          <Text>{count}</Text>
        </Space>
      ),
    },
    {
      title: 'Guidelines',
      dataIndex: 'has_guidelines',
      key: 'has_guidelines',
      render: (hasGuidelines: boolean) => (
        <Tag color={hasGuidelines ? 'green' : 'red'}>
          {hasGuidelines ? 'Yes' : 'No'}
        </Tag>
      ),
    },
    {
      title: 'Analysis Date',
      dataIndex: 'analysis_date',
      key: 'analysis_date',
      render: (date: string) => (
        <Text style={{ color: '#8c8c8c' }}>
          {new Date(date).toLocaleDateString()}
        </Text>
      ),
      sorter: (a: RepositoryAnalysis, b: RepositoryAnalysis) => 
        new Date(a.analysis_date).getTime() - new Date(b.analysis_date).getTime(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (_, record: RepositoryAnalysis) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => showDetails(record)}
          >
            Details
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ color: '#ffffff', margin: 0 }}>
          Repository Analysis
        </Title>
        <Button 
          icon={<ReloadOutlined />} 
          onClick={loadAnalyses}
          loading={loading}
        >
          Refresh
        </Button>
      </div>

      <Card className="dashboard-card" style={{ marginBottom: 24 }}>
        <Space direction="vertical" style={{ width: '100%' }}>
          <Text style={{ color: '#ffffff' }}>
            Analyze a new repository to discover contribution opportunities
          </Text>
          <Search
            placeholder="Enter repository name (e.g., bitcoin/bitcoin)"
            enterButton={
              <Button type="primary" icon={<SearchOutlined />} loading={analyzing}>
                Analyze
              </Button>
            }
            size="large"
            onSearch={analyzeRepository}
            style={{ maxWidth: 600 }}
          />
        </Space>
      </Card>

      <Card className="dashboard-card">
        <Table
          columns={columns}
          dataSource={analyses}
          rowKey="id"
          loading={loading}
          pagination={{
            pageSize: 10,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `${range[0]}-${range[1]} of ${total} analyses`,
          }}
          scroll={{ x: 1200 }}
        />
      </Card>

      <Modal
        title={
          <Space>
            <FileTextOutlined />
            <span>Repository Analysis Details</span>
          </Space>
        }
        open={detailsVisible}
        onCancel={() => setDetailsVisible(false)}
        footer={null}
        width={800}
      >
        {selectedAnalysis && (
          <div>
            <Alert
              message={selectedAnalysis.recommendation}
              type={selectedAnalysis.health_score >= 70 ? 'success' : 'warning'}
              style={{ marginBottom: 16 }}
            />
            
            <Descriptions bordered column={2}>
              <Descriptions.Item label="Repository">
                {selectedAnalysis.repository}
              </Descriptions.Item>
              <Descriptions.Item label="Health Score">
                <Progress
                  percent={selectedAnalysis.health_score}
                  size="small"
                  strokeColor={getHealthScoreColor(selectedAnalysis.health_score)}
                  style={{ width: 150 }}
                />
              </Descriptions.Item>
              <Descriptions.Item label="Activity Level">
                <Tag color={getActivityLevelColor(selectedAnalysis.activity_level)}>
                  {selectedAnalysis.activity_level.replace('_', ' ').toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Contribution Difficulty">
                <Tag color={getDifficultyColor(selectedAnalysis.contribution_difficulty)}>
                  {selectedAnalysis.contribution_difficulty.toUpperCase()}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Good First Issues">
                <Space>
                  <BugOutlined style={{ color: '#52c41a' }} />
                  <Text>{selectedAnalysis.good_first_issues}</Text>
                </Space>
              </Descriptions.Item>
              <Descriptions.Item label="Has Guidelines">
                <Tag color={selectedAnalysis.has_guidelines ? 'green' : 'red'}>
                  {selectedAnalysis.has_guidelines ? 'Yes' : 'No'}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Analysis Date" span={2}>
                {new Date(selectedAnalysis.analysis_date).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>
          </div>
        )}
      </Modal>
    </div>
  );
};

export default RepositoryAnalysisPage;
