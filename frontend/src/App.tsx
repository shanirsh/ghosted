import React, { useState, useRef, useEffect } from 'react';
import { styled, keyframes } from '@mui/material/styles';
import { TextField, Box, IconButton } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import StopIcon from '@mui/icons-material/Stop';
import logo from './images/update-removebg-preview.png';
import './App.css';
import './styles/mobile.css';
import Config from './components/Config';
import Sidebar from './components/Sidebar';
import DeploymentsPage from './pages/Deployments';
import {
  formatInstance,
  formatBucketDetailed,
  formatBucketSimple,
  formatS3Object,
  findInstances,
  findBuckets,
  findS3Objects,
} from './formatters';

const fadeIn = keyframes`
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const pulse = keyframes`
  0% {
    opacity: 0.85;
    transform: scale(1);
    filter: drop-shadow(0 0 15px rgba(74, 246, 38, 0.2));
  }
  50% {
    opacity: 0.95;
    transform: scale(1.01);
    filter: drop-shadow(0 0 25px rgba(74, 246, 38, 0.3));
  }
  100% {
    opacity: 0.85;
    transform: scale(1);
    filter: drop-shadow(0 0 15px rgba(74, 246, 38, 0.2));
  }
`;

const fadeDots = keyframes`
  0% {
    opacity: 0.2;
  }
  50% {
    opacity: 1;
  }
  100% {
    opacity: 0.2;
  }
`;

const blink = keyframes`
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0;
  }
`;

const pageTransition = keyframes`
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

const pageExit = keyframes`
  from {
    opacity: 1;
    transform: translateY(0);
  }
  to {
    opacity: 0;
    transform: translateY(-20px);
  }
`;

const DeploymentsWrapper = styled(Box)({
  width: '100%',
  height: '100vh',
  position: 'fixed',
  top: 0,
  left: 0,
  zIndex: 1000,
  overflowY: 'auto',
  overflowX: 'hidden',
  scrollbarWidth: 'none',
  msOverflowStyle: 'none',
  animation: `${pageTransition} 0.4s ease-out`,
  '&::-webkit-scrollbar': {
    display: 'none'
  },
  '&.exiting': {
    animation: `${pageExit} 0.3s ease-in forwards`
  }
});

const typewriter = keyframes`
  from {
    width: 0;
  }
  to {
    width: 100%;
  }
`;

const TerminalContainer = styled('div')({
  display: 'flex',
  flexDirection: 'column',
  height: '100vh', // Use height instead of minHeight to contain content
  backgroundColor: '#000000',
  backgroundImage: 'radial-gradient(circle at center, rgba(255,255,255,0.02) 0%, rgba(0,0,0,0) 100%)',
  color: '#ffffff',
  fontFamily: "'Söhne Mono', monospace",
  padding: '0 15%',
  maxWidth: '700px',
  margin: '0 auto',
  position: 'relative',
  overflow: 'hidden', // Prevent scrolling on the container itself
  '@media (max-width: 768px)': {
    padding: '0 5%',
  },
});

const Header = styled('div')({
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '1.5rem 0',
  marginBottom: '0.5rem',
  '@media (max-width: 768px)': {
    padding: '1.5rem 0',
  },
});

const LogoLink = styled('a')({
  cursor: 'pointer',
  textDecoration: 'none',
  '&:hover': {
    opacity: 0.9,
  },
});

const Logo = styled('img')({
  height: '160px',
  filter: 'invert(1) opacity(0.85)',
  animation: `${pulse} 4s ease-in-out infinite`,
  transition: 'all 0.3s ease',
  '@media (max-width: 768px)': {
    height: '120px',
  },
  '&:hover': {
    filter: 'invert(1) opacity(0.95)',
    transform: 'scale(1.02)',
  }
});

const MessagesContainer = styled('div')({
  flex: 1,
  overflowY: 'auto',
  padding: '1.5rem 0',
  marginBottom: '80px', // Add more space at the bottom for the input container
  display: 'flex',
  flexDirection: 'column',
  maxHeight: 'calc(100vh - 180px)', // Adjust height to account for header and input
  '&::-webkit-scrollbar': {
    width: '4px',
  },
  '&::-webkit-scrollbar-track': {
    background: 'rgba(255, 255, 255, 0.05)',
  },
  '&::-webkit-scrollbar-thumb': {
    background: 'rgba(255, 255, 255, 0.1)',
    borderRadius: '2px',
  },
});

const Message = styled('div')({
  marginBottom: '2rem', // Reduced margin to fit more messages
  animation: `${fadeIn} 0.3s ease-out`,
  whiteSpace: 'pre-wrap',
  lineHeight: '1.6',
  fontSize: '0.95rem',
  letterSpacing: '0.3px',
  maxWidth: '100%',
  position: 'relative',
  padding: '0.75rem 0',
  overflowWrap: 'break-word', // Ensure long words don't overflow
  wordBreak: 'break-word', // Additional support for breaking long words
});

const UserMessage = styled(Message)({
  color: '#00FF7F',
  textAlign: 'left',
  display: 'flex',
  alignItems: 'center',
  '&::before': {
    content: '"ghosted:~$ "',
    color: '#00FF7F',
    marginRight: '0.5rem',
  },
});

const AssistantMessage = styled(Message)({
  color: '#EDEDED',
  fontFamily: "'Söhne Mono', monospace",
  textAlign: 'left',
  position: 'relative',
  '&::after': {
    content: '""',
    position: 'absolute',
    top: 0,
    left: 0,
    width: '100%',
    height: '100%',
    background: 'linear-gradient(to right, transparent, rgba(0,0,0,0.05), transparent)',
    animation: `${typewriter} 2s steps(40, end)`,
  },
});

const InputContainer = styled('div')({
  position: 'fixed',
  bottom: 0,
  left: 0,
  right: 0,
  padding: '0.5rem 10% 0.75rem',
  backgroundColor: 'rgba(0, 0, 0, 0.9)',
  borderTop: '1px solid rgba(0, 255, 127, 0.1)',
  maxWidth: '550px',
  margin: '0 auto',
  zIndex: 10, // Ensure input stays on top
  boxShadow: '0 -5px 15px rgba(0, 0, 0, 0.9)', // More subtle shadow
  backdropFilter: 'blur(5px)',
  '@media (max-width: 768px)': {
    padding: '0.5rem 5% 0.75rem',
  },
});

const Prompt = styled('span')({
  color: '#00FF7F',
  marginRight: '0.5rem',
  fontFamily: "'Söhne Mono', monospace",
  fontSize: '0.95rem',
  whiteSpace: 'nowrap',
});

const Cursor = styled('span')({
  display: 'inline-block',
  width: '8px',
  height: '1.2em',
  backgroundColor: '#00FF7F',
  marginLeft: '2px',
  animation: `${blink} 1s step-end infinite`,
  verticalAlign: 'middle',
});

const StyledTextField = styled(TextField)({
  '& .MuiOutlinedInput-root': {
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    color: '#00FF7F',
    fontFamily: '"Fira Code", monospace',
    fontSize: '14px',
    padding: '4px 8px',
    height: '38px',
    '& fieldset': {
      borderColor: 'rgba(0, 255, 127, 0.3)',
      borderWidth: '1px',
      borderRadius: '4px',
    },
    '&:hover fieldset': {
      borderColor: 'rgba(0, 255, 127, 0.6)',
      boxShadow: '0 0 8px rgba(0, 255, 127, 0.2)',
    },
    '&.Mui-focused fieldset': {
      borderColor: '#00FF7F',
      boxShadow: '0 0 10px rgba(0, 255, 127, 0.3)',
    },
  },
  '& .MuiOutlinedInput-input': {
    padding: '8px 10px',
  },
  '& .MuiInputBase-input::placeholder': {
    color: 'rgba(255, 255, 255, 0.3)',
  },
});

const LoadingDots = styled('span')({
  '&::after': {
    content: '"..."',
    animation: `${fadeDots} 1.4s infinite`,
  },
});

const CommandButton = styled(IconButton)({
  position: 'absolute',
  right: '8px',
  top: '50%',
  transform: 'translateY(-50%)',
  width: '32px',
  height: '32px',
  padding: '4px',
  zIndex: 10,
  transition: 'all 0.2s ease',
  '&.send': {
    color: 'rgba(0, 255, 127, 0.8)',
    '&:hover': {
      color: 'rgba(0, 255, 127, 1)',
      backgroundColor: 'rgba(0, 255, 127, 0.1)',
    },
  },
  '&.stop': {
    color: 'rgba(244, 67, 54, 0.8)',
    '&:hover': {
      color: 'rgba(244, 67, 54, 1)',
      backgroundColor: 'rgba(244, 67, 54, 0.1)',
    },
  },
});

interface ChatMessage {
  content: string;
  type: 'user' | 'assistant';
  timestamp?: string;
}

function App() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const [isConfigured, setIsConfigured] = useState(false);
  const [roleArn, setRoleArn] = useState<string | null>(null);
  const [awsRegion, setAwsRegion] = useState<string | null>(null);
  const [externalId, setExternalId] = useState<string | null>(null);
  const [notifications, setNotifications] = useState<Array<{ type: 'success' | 'error'; message: string; id: number }>>([]);
  const [currentPage, setCurrentPage] = useState<'chat' | 'deployments'>('chat');

  const scrollToBottom = () => {
    if (messagesEndRef.current) {
      // Use a small timeout to ensure the DOM has updated
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' });
      }, 100);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleConfigSubmit = async (config: { roleArn: string; awsRegion: string; externalId: string }): Promise<void> => {
    // Store the credentials
    setRoleArn(config.roleArn);
    setAwsRegion(config.awsRegion);
    setExternalId(config.externalId);
    
    // Return a promise that resolves after the transition animation duration
    // This allows the Config component to show its transition animation
    return new Promise(resolve => {
      setTimeout(() => {
        setIsConfigured(true);
        showNotification('success', 'AWS credentials configured successfully!');
        resolve();
      }, 2500); // Match this with the transition duration in Config.tsx
    });
  };

  const showNotification = (type: 'success' | 'error', message: string) => {
    const id = Date.now();
    setNotifications(prev => [...prev, { type, message, id }]);
    setTimeout(() => {
      setNotifications(prev => prev.filter(notification => notification.id !== id));
    }, 3000);
  };

  const handleNavigation = (page: string) => {
    switch(page) {
      case 'deployments':
        setCurrentPage('deployments');
        break;
      default:
        setCurrentPage('chat');
    }
  };

  // Function to handle stopping a command
  const handleStopCommand = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
      setIsProcessing(false);
      setIsLoading(false);
      setMessages(prev => [...prev, { 
        content: 'Command execution was stopped by user.', 
        type: 'assistant' 
      }]);
    }
  };

  // Handle keyboard shortcuts (ESC to stop command)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isProcessing) {
        handleStopCommand();
      }
    };
    
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isProcessing]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const userMessage = input.trim();
    if (!userMessage) return;

    setMessages(prev => [...prev, { content: userMessage, type: 'user', timestamp: new Date().toISOString() }]);
    setInput('');

    try {
      setIsLoading(true);
      setIsProcessing(true);
      abortControllerRef.current = new AbortController();

      const apiUrl = `${process.env.REACT_APP_API_URL || 'http://localhost:8000'}/api/ai/process`;

      let userId = localStorage.getItem('user_id');
      if (!userId) {
        userId = 'user_' + Date.now();
        localStorage.setItem('user_id', userId);
      }

      const payload = {
        command: userMessage,
        role_arn: roleArn,
        region: awsRegion,
        external_id: externalId,
        user_id: userId,
        conversation_history: messages.map(msg => ({
          role: msg.type === 'user' ? 'user' : 'assistant',
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
        })),
        frontend_request: true,
      };

      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) throw new Error(`API error: ${response.status} ${response.statusText}`);

      let data: any;
      try {
        data = await response.json();
        if (!data) {
          setMessages(prev => [...prev, { content: 'Sorry, I encountered an error. Please try again later.', type: 'assistant' }]);
          return;
        }
      } catch {
        setMessages(prev => [...prev, { content: 'Sorry, I encountered an error. Please try again later.', type: 'assistant' }]);
        return;
      }

      setIsLoading(false);

      // Extract base response content from various formats
      let responseContent =
        data.content || data.response || data.message ||
        (typeof data === 'string' ? data : null) ||
        (data.error?.message ? `Error: ${data.error.message}` : null) ||
        data.data?.content || data.data?.message ||
        'I processed your request, but the response format was unexpected.';

      // Format pre-structured result messages
      if (data.content && data.result) {
        const msg = data.result.message;
        if (typeof msg === 'string') {
          responseContent = msg;
        } else if (data.result.Instances) {
          responseContent = `${data.content}\n\n` + data.result.Instances.map((inst: any) =>
            formatInstance(inst)
          ).join('\n');
        } else if (data.result.Buckets) {
          responseContent = `${data.content}\n\n` + data.result.Buckets.map((b: any) =>
            `- **${b.Name}**${b.CreationDate ? ` (Created: ${new Date(b.CreationDate).toLocaleDateString()})` : ''}`
          ).join('\n');
        } else if (data.result.Contents) {
          responseContent = `${data.content}\n\n` + data.result.Contents.map((item: any) =>
            `- **${item.Key}**${item.Size ? ` (${Math.round(item.Size / 1024 * 100) / 100} KB)` : ''}${item.LastModified ? ` - Modified: ${new Date(item.LastModified).toLocaleDateString()}` : ''}`
          ).join('\n');
        }
      }

      let formattedContent = responseContent;
      const nestedData = data.data && typeof data.data === 'object' && !Array.isArray(data.data) ? data.data : null;

      // S3 bucket deletion
      if (data.bucket?.action === 'deleted') {
        formattedContent += `\n\n**S3 Bucket Deletion Confirmed**\n\nI've successfully deleted '${data.bucket.name}' from the ${data.bucket.region || 'us-east-1'} region.`;
      }

      // Confirmation request
      if (data.type === 'confirmation' && data.proposed_action?.includes('delete s3 bucket')) {
        formattedContent = `**Warning: Confirmation Required**\n\n${formattedContent}`;
      }

      // S3 bucket created
      if (data.bucket?.name && data.bucket?.action !== 'deleted') {
        const { name, region: r = 'us-east-1' } = data.bucket;
        const link = data.bucket.console_link || `https://s3.console.aws.amazon.com/s3/buckets/${name}?region=${r}`;
        formattedContent += `\n\n**S3 Bucket Created:**\n- **Name:** ${name}\n- **Region:** ${r}\n- **Console Link:** [Open in AWS Console](${link})\n`;
      }

      // EC2 instance created (from data.instance)
      if (data.instance) {
        const ids = Array.isArray(data.instance.ids) ? data.instance.ids : [data.instance.ids || data.instance.id].filter(Boolean);
        const iType = data.instance.type || 't2.micro';
        const r = data.instance.region || 'us-east-1';
        if (ids.length > 0) {
          formattedContent += '\n\n**EC2 Instance Created:**\n';
          ids.forEach((id: string) => {
            formattedContent += `- **Instance ID:** ${id}\n- **Type:** ${iType}\n- **Region:** ${r}\n- **Console Link:** [Open in AWS Console](https://${r}.console.aws.amazon.com/ec2/home?region=${r}#InstanceDetails:instanceId=${id})\n\n`;
          });
        }
      }

      // Format EC2 instances from any nesting level
      const instances = findInstances(data);
      if (instances.length > 0) {
        formattedContent += '\n\n**EC2 Instances:**\n';
        formattedContent += instances.map((inst: any) => formatInstance(inst.details || inst, data.region)).join('\n');
      }

      // Format S3 buckets from any nesting level
      const { buckets, details: bucketDetails } = findBuckets(data);
      if (buckets.length > 0) {
        formattedContent += '\n\n**S3 Buckets:**\n';
        if (bucketDetails.length > 0) {
          formattedContent += bucketDetails.map(formatBucketDetailed).join('\n');
        } else {
          formattedContent += buckets.map(formatBucketSimple).join('\n');
        }
      } else if (data.buckets !== undefined && !buckets.length) {
        formattedContent = '**S3 Buckets:**\n';
        if (data.message?.includes('list_buckets')) {
          formattedContent += 'No S3 buckets found in this region. Would you like me to create one?\n';
          formattedContent += '\nView buckets in the [AWS S3 Console](https://s3.console.aws.amazon.com/s3/buckets).\n';
        } else {
          formattedContent += 'No S3 buckets found.\n';
        }
      }

      // Format S3 objects from any nesting level
      const s3Objects = findS3Objects(data);
      if (s3Objects.length > 0) {
        formattedContent += '\n\n' + s3Objects.map(formatS3Object).join('\n');
      }

      // Handle created instance details from deeply nested sources
      const hasCreatedInstance = data.instance_id || data.instanceId ||
        nestedData?.instance_id || nestedData?.instanceId;
      if (hasCreatedInstance && instances.length === 0) {
        const instanceData = data.instance || nestedData?.instance;
        const dataField = nestedData || {};
        let instanceIds: string[] = [];
        if (instanceData?.ids) instanceIds = [].concat(instanceData.ids);
        else if (dataField.instance_ids) instanceIds = [].concat(dataField.instance_ids);
        else if (data.instance_ids) instanceIds = [].concat(data.instance_ids);
        else if (data.instanceId) instanceIds = [data.instanceId];
        else if (data.instance_id) instanceIds = [data.instance_id];

        const iType = instanceData?.type || dataField.instance_type || 'Unknown';
        const r = instanceData?.region || dataField.region || 'us-east-1';

        if (instanceIds.length > 0) {
          formattedContent += '\n\n**EC2 Instance Details:**\n';
          instanceIds.forEach((id: string) => {
            formattedContent += `- **Instance ID:** ${id}\n- **Type:** ${iType}\n- **Region:** ${r}\n- [View in AWS Console](https://${r}.console.aws.amazon.com/ec2/home?region=${r}#InstanceDetails:instanceId=${id})\n\n`;
          });
        }
      }

      // Handle created bucket details from deeply nested sources
      const hasCreatedBucket = data.bucket_name || data.bucketName || nestedData?.bucket_name;
      if (hasCreatedBucket && buckets.length === 0) {
        const bName = data.bucket_name || data.bucketName || nestedData?.bucket_name || 'Unknown';
        const bRegion = data.region || nestedData?.region || 'us-east-1';
        const bLink = data.console_link || nestedData?.console_link || `https://s3.console.aws.amazon.com/s3/buckets/${bName}?region=${bRegion}`;
        if (!formattedContent.includes(bName) || !formattedContent.includes('console.aws.amazon.com')) {
          formattedContent += `\n\nCreated S3 Bucket:\n- Name: ${bName}\n- Region: ${bRegion}\n- [View in AWS Console](${bLink})`;
        }
      }

      // Handle nested messages
      if (nestedData?.message && typeof nestedData.message === 'string') {
        if (data.message?.toLowerCase().includes('bucket')) {
          if (data.message.toLowerCase().includes('deleted') || nestedData.message.toLowerCase().includes('deleted')) {
            formattedContent = nestedData.message;
          } else {
            formattedContent = data.message;
            if (nestedData.console_link) formattedContent += `\n\n[View in AWS Console](${nestedData.console_link})`;
          }
        } else if (nestedData.success === false || nestedData.error) {
          formattedContent = `${data.message}\n\nError: ${nestedData.message}`;
        } else if (!formattedContent.includes(nestedData.message)) {
          formattedContent += `\n\n${nestedData.message}`;
        }
      }

      const hasAwsResources = instances.length > 0 || buckets.length > 0 || s3Objects.length > 0 ||
        data.bucket || data.instance || hasCreatedInstance || hasCreatedBucket ||
        data.buckets !== undefined;

      if (hasAwsResources) {
        setMessages(prev => [...prev, { content: formattedContent, type: 'assistant', timestamp: new Date().toISOString() }]);
      } else {
        const finalContent = data.message || nestedData?.message || responseContent || '';
        setMessages(prev => [...prev, { content: finalContent, type: 'assistant', timestamp: new Date().toISOString() }]);
        if (data.type === 'success' || data.success) {
          showNotification('success', 'Command processed successfully!');
        } else if (data.type === 'error' || data.error) {
          showNotification('error', finalContent);
        }
      }
    } catch (error) {
      setMessages(prev => [...prev, { content: 'Sorry, I encountered an error. Please try again.', type: 'assistant', timestamp: new Date().toISOString() }]);
      showNotification('error', 'Failed to process your request');
    } finally {
      setIsLoading(false);
      setIsProcessing(false);
      abortControllerRef.current = null;
    }
  };

  return (
    <div className="app">
      {!isConfigured ? (
        <Config 
          onConfigSubmit={handleConfigSubmit} 
          ghostOpsAccountId={process.env.REACT_APP_GHOSTED_ACCOUNT_ID || ''}
        />
      ) : (
        <>
          <Sidebar 
            roleArn={roleArn || ''} 
            region={awsRegion || ''} 
            externalId={externalId || ''} 
            onNavigate={handleNavigation}
            currentPage={currentPage}
          />
          
          {/* Main content area with page switching */}
          {currentPage === 'deployments' && (
            <DeploymentsWrapper id="deployments-wrapper">
              <DeploymentsPage 
                roleArn={roleArn || ''} 
                region={awsRegion || ''} 
                externalId={externalId || ''} 
                onBack={() => {
                  // Add exit animation before changing page
                  const wrapper = document.getElementById('deployments-wrapper');
                  if (wrapper) {
                    wrapper.classList.add('exiting');
                    // Wait for animation to complete before changing page
                    setTimeout(() => setCurrentPage('chat'), 280);
                  } else {
                    setCurrentPage('chat');
                  }
                }}
              />
            </DeploymentsWrapper>
          )}
          
          {currentPage === 'chat' && (
            <TerminalContainer>
              <Header>
                <LogoLink href="/">
                  <Logo src={logo} alt="Ghosted Logo" />
                </LogoLink>
              </Header>

              <MessagesContainer>
                {messages.map((message, index) => (
                  message.type === 'user' ? (
                    <UserMessage key={index}>{message.content}</UserMessage>
                  ) : (
                    <AssistantMessage key={index}>{message.content}</AssistantMessage>
                  )
                ))}
                {isLoading && (
                  <AssistantMessage>
                    ghosted is thinking <LoadingDots />
                  </AssistantMessage>
                )}
                <div ref={messagesEndRef} />
              </MessagesContainer>

              <InputContainer>
                <form onSubmit={handleSubmit} style={{ display: 'flex', alignItems: 'center', position: 'relative' }}>
                  <Prompt>ghosted:~$</Prompt>
                  <div style={{ position: 'relative', width: '100%', display: 'flex', alignItems: 'center' }}>
                    <StyledTextField
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder=""
                      variant="outlined"
                      fullWidth
                      autoComplete="off"
                      disabled={isProcessing}
                      sx={{ paddingRight: '40px' }}
                    />
                    {!isProcessing && !input && (
                      <Cursor 
                        style={{ 
                          position: 'absolute', 
                          right: '50px',
                          backgroundColor: '#00FF7F',
                          opacity: 0.7
                        }} 
                      />
                    )}
                  </div>
                  <CommandButton 
                    className={isProcessing ? 'stop' : 'send'}
                    onClick={isProcessing ? handleStopCommand : handleSubmit}
                    size="small"
                    aria-label={isProcessing ? 'Stop command' : 'Send command'}
                    type={isProcessing ? 'button' : 'submit'}
                  >
                    {isProcessing ? <StopIcon fontSize="small" /> : <SendIcon fontSize="small" />}
                  </CommandButton>
                </form>
              </InputContainer>

              <div className="notifications">
                {notifications.map((notification, index) => (
                  <div key={index} className={`notification ${notification.type}`}>
                    {notification.message}
                  </div>
                ))}
              </div>
            </TerminalContainer>
          )}
          </>
      )}
    </div>
  );
}

export default App;
