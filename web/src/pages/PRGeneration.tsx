import React, { useState, useEffect } from 'react';
import { 
  Card, 
  Form, 
  Input, 
  Select, 
  Button, 
  Space, 
  Typography, 
  Alert,
  Divider,
  Switch,
  InputNumber,
  message,
  Modal,
  Descriptions,
  Tag,
  Progress
} from 'antd';
import { 
  CodeOutlined, 
  SendOutlined, 
  EyeOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { apiService, Opportunity, PRGenerationResult } from '../services/api';

const { Title, Text, Paragraph } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const PRGenerationPage: React.FC = () => {
  const [form] = Form.useForm();
  const [opportunities, setOpportunities] = useState<Opportunity[]>([]);
  const [generating, setGenerating] = useState(false);
  const [generationResult, setGenerationResult] = useState<PRGenerationResult | null>(null);
  const [previewVisible, setPreviewVisible] = useState(false);

  useEffect(() => {
    loadOpportunities();
  }, []);

  const loadOpportunities = async () => {
    try {
      const response = await apiService.getOpportunities(undefined, 50);
      setOpportunities(response.data);
    } catch (error) {
      console.error('Failed to load opportunities:', error);
    }
  };

  const generatePR = async (values: any) => {
    try {
      setGenerating(true);
      
      const request = {
        repository: values.repository,
        opportunity_id: values.opportunity_id,
        type: values.type,
        issue_number: values.issue_number,
        dry_run: values.dry_run !== false, // Default to true
      };

      const response = await apiService.generatePR(request);
      
      if (response.data.status === 'started') {
        message.success('PR generation started! Check back in a few minutes.');
      } else {
        setGenerationResult(response.data);
        message.success('PR generated successfully!');
      }
      
    } catch (error) {
      message.error('Failed to generate PR');
      console.error('Failed to generate PR:', error);
    } finally {
      setGenerating(false);
    }
  };

  const showPreview = () => {
    setPreviewVisible(true);
  };

  const getValidationIcon = (valid: boolean) => {
    return valid ? (
      <CheckCircleOutlined style={{ color: '#52c41a' }} />
    ) : (
      <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
    );
  };

  const getValidationColor = (valid: boolean) => {
    return valid ? '#52c41a' : '#ff4d4f';
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <Title level={2} style={{ color: '#ffffff', margin: 0 }}>
          PR Generation
        </Title>
      </div>

      <Alert
        message="Automated Pull Request Generation"
        description="Generate high-quality pull requests automatically based on detected opportunities or specific requirements."
        type="info"
        showIcon
        style={{ marginBottom: 24 }}
      />

      <Card className="pr-generation-form">
        <Form
          form={form}
          layout="vertical"
          onFinish={generatePR}
          initialValues={{
            dry_run: true,
            type: 'bug_fix',
          }}
        >
          <Form.Item
            label="Repository"
            name="repository"
            rules={[{ required: true, message: 'Please enter repository name' }]}
          >
            <Input 
              placeholder="e.g., bitcoin/bitcoin"
              size="large"
            />
          </Form.Item>

          <Divider>Generation Method</Divider>

          <Form.Item
            label="Opportunity ID (Optional)"
            name="opportunity_id"
            help="Select a specific opportunity to generate PR for"
          >
            <Select
              placeholder="Select an opportunity"
              allowClear
              size="large"
              showSearch
              filterOption={(input, option) =>
                option?.children?.toString().toLowerCase().includes(input.toLowerCase()) ?? false
              }
            >
              {opportunities.map(opp => (
                <Option key={opp.id} value={opp.id}>
                  #{opp.id} - {opp.title} ({opp.repository})
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item
            label="PR Type"
            name="type"
            help="Type of PR to generate (used if no specific opportunity selected)"
          >
            <Select size="large">
              <Option value="bug_fix">Bug Fix</Option>
              <Option value="documentation">Documentation</Option>
              <Option value="testing">Testing</Option>
              <Option value="feature">Feature</Option>
            </Select>
          </Form.Item>

          <Form.Item
            label="Issue Number (Optional)"
            name="issue_number"
            help="GitHub issue number for bug fix PRs"
          >
            <InputNumber 
              placeholder="e.g., 12345"
              style={{ width: '100%' }}
              size="large"
            />
          </Form.Item>

          <Form.Item
            label="Dry Run"
            name="dry_run"
            valuePropName="checked"
            help="When enabled, PR will be generated but not actually submitted to GitHub"
          >
            <Switch />
          </Form.Item>

          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<CodeOutlined />}
                loading={generating}
                size="large"
              >
                Generate PR
              </Button>
              {generationResult && (
                <Button
                  icon={<EyeOutlined />}
                  onClick={showPreview}
                  size="large"
                >
                  View Result
                </Button>
              )}
            </Space>
          </Form.Item>
        </Form>
      </Card>

      {generationResult && (
        <Card 
          className="dashboard-card" 
          title={
            <Space>
              <CodeOutlined />
              <span>Generation Result</span>
              <Tag color={generationResult.status === 'success' ? 'green' : 'red'}>
                {generationResult.status.toUpperCase()}
              </Tag>
            </Space>
          }
          style={{ marginTop: 24 }}
        >
          {generationResult.status === 'success' ? (
            <div>
              <Descriptions bordered column={2} style={{ marginBottom: 16 }}>
                <Descriptions.Item label="Branch Name">
                  <Text code>{generationResult.solution?.branchName}</Text>
                </Descriptions.Item>
                <Descriptions.Item label="Changes">
                  {generationResult.solution?.changes?.length || 0} files
                </Descriptions.Item>
                <Descriptions.Item label="Validation Score" span={2}>
                  <Space>
                    {getValidationIcon(generationResult.validation?.valid || false)}
                    <Progress
                      percent={generationResult.validation?.score || 0}
                      size="small"
                      strokeColor={getValidationColor(generationResult.validation?.valid || false)}
                      style={{ width: 200 }}
                    />
                  </Space>
                </Descriptions.Item>
              </Descriptions>

              {generationResult.validation && (
                <div>
                  {generationResult.validation.warnings.length > 0 && (
                    <Alert
                      message="Validation Warnings"
                      description={
                        <ul>
                          {generationResult.validation.warnings.map((warning, index) => (
                            <li key={index}>{warning}</li>
                          ))}
                        </ul>
                      }
                      type="warning"
                      style={{ marginBottom: 16 }}
                    />
                  )}

                  {generationResult.validation.errors.length > 0 && (
                    <Alert
                      message="Validation Errors"
                      description={
                        <ul>
                          {generationResult.validation.errors.map((error, index) => (
                            <li key={index}>{error}</li>
                          ))}
                        </ul>
                      }
                      type="error"
                      style={{ marginBottom: 16 }}
                    />
                  )}
                </div>
              )}

              {generationResult.pr && (
                <Alert
                  message="PR Created Successfully"
                  description={
                    <div>
                      <p>PR #{generationResult.pr.prNumber} has been created.</p>
                      <a 
                        href={generationResult.pr.prUrl} 
                        target="_blank" 
                        rel="noopener noreferrer"
                      >
                        View PR on GitHub
                      </a>
                    </div>
                  }
                  type="success"
                  showIcon
                />
              )}
            </div>
          ) : (
            <Alert
              message="Generation Failed"
              description="The PR generation process encountered an error. Please check the logs for more details."
              type="error"
              showIcon
            />
          )}
        </Card>
      )}

      <Modal
        title="PR Generation Details"
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width={1000}
      >
        {generationResult && (
          <div>
            <Descriptions bordered column={1} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="Commit Message">
                <Text code>{generationResult.solution?.commitMessage}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="Generated At">
                {new Date(generationResult.generatedAt).toLocaleString()}
              </Descriptions.Item>
            </Descriptions>

            {generationResult.solution?.changes && generationResult.solution.changes.length > 0 && (
              <div>
                <Title level={4}>Code Changes</Title>
                {generationResult.solution.changes.slice(0, 3).map((change: any, index: number) => (
                  <Card key={index} size="small" style={{ marginBottom: 16 }}>
                    <div style={{ marginBottom: 8 }}>
                      <Tag color="blue">{change.type}</Tag>
                      <Text code>{change.file_path}</Text>
                    </div>
                    <SyntaxHighlighter
                      language="javascript"
                      style={tomorrow}
                      customStyle={{
                        background: '#000000',
                        fontSize: '12px',
                        maxHeight: '300px',
                        overflow: 'auto',
                      }}
                    >
                      {change.content?.substring(0, 1000) || 'No content preview available'}
                    </SyntaxHighlighter>
                    {change.content && change.content.length > 1000 && (
                      <Text style={{ color: '#8c8c8c' }}>... (truncated)</Text>
                    )}
                  </Card>
                ))}
                {generationResult.solution.changes.length > 3 && (
                  <Text style={{ color: '#8c8c8c' }}>
                    ... and {generationResult.solution.changes.length - 3} more files
                  </Text>
                )}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default PRGenerationPage;
