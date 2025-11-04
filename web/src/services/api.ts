import axios, { AxiosInstance, AxiosResponse } from 'axios';

export interface ApiResponse<T = any> {
  data: T;
  status: number;
  message?: string;
}

export interface RepositoryAnalysis {
  id: number;
  repository: string;
  health_score: number;
  activity_level: string;
  contribution_difficulty: string;
  good_first_issues: number;
  has_guidelines: boolean;
  analysis_date: string;
  recommendation: string;
}

export interface Opportunity {
  id: number;
  repository: string;
  type: string;
  title: string;
  description: string;
  complexity: string;
  skills_required: string[];
  score: number;
  issue_number?: number;
  created_at: string;
}

export interface ContributionAttempt {
  id: number;
  opportunity_id: number;
  repository: string;
  status: string;
  pr_number?: number;
  pr_url?: string;
  notes?: string;
  created_at: string;
}

export interface DashboardStats {
  totalAnalyses: number;
  totalOpportunities: number;
  totalContributions: number;
  successRate: number;
  activeRepositories: number;
}

export interface RecentActivity {
  id: string;
  type: 'analysis' | 'opportunity' | 'contribution';
  repository: string;
  description: string;
  timestamp: string;
  status: 'success' | 'pending' | 'failed';
}

export interface PRGenerationRequest {
  repository: string;
  opportunityId?: number;
  type?: 'bug_fix' | 'documentation' | 'testing' | 'feature';
  issueNumber?: number;
  dryRun?: boolean;
}

export interface PRGenerationResult {
  status: string;
  opportunityId?: number;
  solution?: {
    branchName: string;
    commitMessage: string;
    changes: any[];
  };
  validation?: {
    valid: boolean;
    score: number;
    warnings: string[];
    errors: string[];
  };
  pr?: {
    prNumber: number;
    prUrl: string;
    status: string;
  };
  generatedAt: string;
}

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: process.env.REACT_APP_API_URL || '/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor
    this.api.interceptors.request.use(
      (config) => {
        // Add auth token if available
        const token = localStorage.getItem('auth_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => {
        return Promise.reject(error);
      }
    );

    // Response interceptor
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          // Handle unauthorized access
          localStorage.removeItem('auth_token');
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  // Dashboard APIs
  async getDashboardStats(): Promise<ApiResponse<DashboardStats>> {
    try {
      const response = await this.api.get('/dashboard/stats');
      return response.data;
    } catch (error) {
      // Mock data for development
      return {
        data: {
          totalAnalyses: 42,
          totalOpportunities: 156,
          totalContributions: 23,
          successRate: 87.5,
          activeRepositories: 8,
        },
        status: 200,
      };
    }
  }

  async getRecentActivity(): Promise<ApiResponse<RecentActivity[]>> {
    try {
      const response = await this.api.get('/dashboard/activity');
      return response.data;
    } catch (error) {
      // Mock data for development
      return {
        data: [
          {
            id: '1',
            type: 'analysis',
            repository: 'bitcoin/bitcoin',
            description: 'Repository analysis completed',
            timestamp: new Date().toISOString(),
            status: 'success',
          },
          {
            id: '2',
            type: 'opportunity',
            repository: 'ethereum/go-ethereum',
            description: 'Found 5 new contribution opportunities',
            timestamp: new Date(Date.now() - 3600000).toISOString(),
            status: 'success',
          },
          {
            id: '3',
            type: 'contribution',
            repository: 'microsoft/vscode',
            description: 'PR #12345 created successfully',
            timestamp: new Date(Date.now() - 7200000).toISOString(),
            status: 'pending',
          },
        ],
        status: 200,
      };
    }
  }

  async getAnalyticsData(period: string): Promise<ApiResponse<any[]>> {
    try {
      const response = await this.api.get(`/analytics/data?period=${period}`);
      return response.data;
    } catch (error) {
      // Mock data for development
      const mockData = [];
      for (let i = 6; i >= 0; i--) {
        const date = new Date();
        date.setDate(date.getDate() - i);
        mockData.push({
          date: date.toISOString().split('T')[0],
          analyses: Math.floor(Math.random() * 10) + 1,
          opportunities: Math.floor(Math.random() * 20) + 5,
          contributions: Math.floor(Math.random() * 5) + 1,
        });
      }
      return {
        data: mockData,
        status: 200,
      };
    }
  }

  // Repository Analysis APIs
  async analyzeRepository(repository: string): Promise<ApiResponse<RepositoryAnalysis>> {
    const response = await this.api.post('/analysis/analyze', { repository });
    return response.data;
  }

  async getRepositoryAnalyses(limit?: number): Promise<ApiResponse<RepositoryAnalysis[]>> {
    const response = await this.api.get(`/analysis/list${limit ? `?limit=${limit}` : ''}`);
    return response.data;
  }

  async getRepositoryAnalysis(id: number): Promise<ApiResponse<RepositoryAnalysis>> {
    const response = await this.api.get(`/analysis/${id}`);
    return response.data;
  }

  // Opportunities APIs
  async getOpportunities(repository?: string, limit?: number): Promise<ApiResponse<Opportunity[]>> {
    const params = new URLSearchParams();
    if (repository) params.append('repository', repository);
    if (limit) params.append('limit', limit.toString());
    
    const response = await this.api.get(`/opportunities?${params.toString()}`);
    return response.data;
  }

  async getOpportunity(id: number): Promise<ApiResponse<Opportunity>> {
    const response = await this.api.get(`/opportunities/${id}`);
    return response.data;
  }

  // PR Generation APIs
  async generatePR(request: PRGenerationRequest): Promise<ApiResponse<PRGenerationResult>> {
    const response = await this.api.post('/pr-generation/generate', request);
    return response.data;
  }

  async getPRGenerationHistory(limit?: number): Promise<ApiResponse<PRGenerationResult[]>> {
    const response = await this.api.get(`/pr-generation/history${limit ? `?limit=${limit}` : ''}`);
    return response.data;
  }

  // Contribution Attempts APIs
  async getContributionAttempts(repository?: string): Promise<ApiResponse<ContributionAttempt[]>> {
    const params = repository ? `?repository=${repository}` : '';
    const response = await this.api.get(`/contributions${params}`);
    return response.data;
  }

  async updateContributionStatus(id: number, status: string, notes?: string): Promise<ApiResponse<void>> {
    const response = await this.api.patch(`/contributions/${id}`, { status, notes });
    return response.data;
  }

  // System APIs
  async getSystemStatus(): Promise<ApiResponse<any>> {
    const response = await this.api.get('/system/status');
    return response.data;
  }

  async getSystemConfig(): Promise<ApiResponse<any>> {
    const response = await this.api.get('/system/config');
    return response.data;
  }

  async updateSystemConfig(config: any): Promise<ApiResponse<void>> {
    const response = await this.api.put('/system/config', config);
    return response.data;
  }
}

export const apiService = new ApiService();
export default apiService;
