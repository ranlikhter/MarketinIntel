import { useState } from 'react';
import { Btn, Input, Textarea, Select, Label, Field, Card, Badge, PageHeader, SectionHeader, Alert, Divider, EmptyState, StatCard, Spinner } from '../components/UI';

export default function UIPreview() {
  const [inputValue, setInputValue] = useState('');
  const [selectValue, setSelectValue] = useState('option1');
  const [textareaValue, setTextareaValue] = useState('');

  return (
    <div style={{ background: 'var(--color-light-background)', minHeight: '100vh', padding: '40px 20px' }}>
      <style jsx global>{`
        @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
        @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&display=swap');

        * {
          font-family: 'IBM Plex Sans', sans-serif;
        }

        :root {
          --color-light-background: #F0F0FA;
          --color-light-surface: #FFFFFF;
          --color-light-border: #E0E0E0;
          --color-light-text: #0A0A0F;
          --color-light-textMuted: #606080;
          --color-amber-500: #F59E0B;
          --color-ink-900: #0A0A0F;
          --color-ink-300: #606080;
          --color-ink-400: #3A3A58;
          --color-signal-up: #10B981;
          --color-signal-down: #EF4444;
          --color-glass-light: rgba(255, 255, 255, 0.15);
          --color-glass-borderLight: rgba(255, 255, 255, 0.2);
          --box-shadow-glass: 0 4px 24px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.1);
          --box-shadow-gradient-lg: 0 6px 28px rgba(245,158,11,0.35);
        }

        body {
          background: var(--color-light-background);
          color: var(--color-light-text);
        }

        .ui-preview-container {
          max-width: 1400px;
          margin: 0 auto;
        }

        .section {
          margin-bottom: 60px;
        }

        .section-title {
          font-family: 'Syne', sans-serif;
          font-size: 24px;
          font-weight: 800;
          color: var(--color-light-text);
          margin-bottom: 24px;
          letter-spacing: -0.02em;
          border-bottom: 2px solid var(--color-amber-500);
          padding-bottom: 12px;
        }

        .component-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: 24px;
          margin-bottom: 32px;
        }

        .component-showcase {
          background: var(--color-glass-light);
          border: 1px solid var(--color-glass-borderLight);
          border-radius: 10px;
          padding: 24px;
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
        }

        .component-label {
          font-size: 10px;
          font-family: 'IBM Plex Mono', monospace;
          color: var(--color-light-textMuted);
          text-transform: uppercase;
          letter-spacing: 0.1em;
          margin-bottom: 12px;
        }

        .button-group {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
          margin-bottom: 16px;
        }

        .color-swatch {
          display: inline-flex;
          align-items: center;
          gap: 12px;
          padding: 12px;
          background: var(--color-glass-light);
          border: 1px solid var(--color-glass-borderLight);
          border-radius: 8px;
          margin-bottom: 12px;
        }

        .color-box {
          width: 40px;
          height: 40px;
          border-radius: 6px;
          border: 1px solid var(--color-light-border);
        }

        .color-info {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }

        .color-name {
          font-weight: 600;
          color: var(--color-light-text);
          font-size: 12px;
        }

        .color-value {
          font-family: 'IBM Plex Mono', monospace;
          font-size: 10px;
          color: var(--color-light-textMuted);
        }

        .stat-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 20px;
        }

        .badge-group {
          display: flex;
          gap: 12px;
          flex-wrap: wrap;
          margin-bottom: 16px;
        }

        .form-group {
          margin-bottom: 20px;
        }

        .demo-table {
          width: 100%;
          border-collapse: collapse;
          margin-top: 16px;
        }

        .demo-table th {
          background: rgba(255, 255, 255, 0.7);
          color: var(--color-light-textMuted);
          font-size: 10px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.06em;
          padding: 12px;
          border-bottom: 1px solid var(--color-light-border);
          text-align: left;
          font-family: 'IBM Plex Mono', monospace;
        }

        .demo-table td {
          padding: 12px;
          border-bottom: 1px solid var(--color-light-border);
          color: var(--color-light-text);
          font-size: 13px;
        }

        .demo-table tr:hover td {
          background: rgba(255, 255, 255, 0.5);
        }

        .typography-demo {
          margin-bottom: 24px;
        }

        .typography-demo h1 {
          font-family: 'Syne', sans-serif;
          font-size: 28px;
          font-weight: 800;
          color: var(--color-light-text);
          letter-spacing: -0.03em;
          margin: 0 0 8px 0;
        }

        .typography-demo h2 {
          font-family: 'Syne', sans-serif;
          font-size: 18px;
          font-weight: 700;
          color: var(--color-light-text);
          letter-spacing: -0.02em;
          margin: 0 0 8px 0;
        }

        .typography-demo p {
          font-size: 14px;
          color: var(--color-light-textMuted);
          line-height: 1.6;
          margin: 0;
        }

        .typography-demo code {
          font-family: 'IBM Plex Mono', monospace;
          font-size: 12px;
          color: var(--color-amber-500);
          background: rgba(245, 158, 11, 0.1);
          padding: 2px 6px;
          border-radius: 4px;
        }

        .hero-banner {
          background: linear-gradient(135deg, rgba(245, 158, 11, 0.1), rgba(16, 185, 129, 0.05));
          border: 1px solid var(--color-glass-borderLight);
          border-radius: 12px;
          padding: 40px;
          text-align: center;
          margin-bottom: 40px;
          backdrop-filter: blur(10px);
          -webkit-backdrop-filter: blur(10px);
        }

        .hero-banner h1 {
          font-family: 'Syne', sans-serif;
          font-size: 32px;
          font-weight: 800;
          color: var(--color-light-text);
          letter-spacing: -0.03em;
          margin: 0 0 12px 0;
        }

        .hero-banner p {
          font-size: 16px;
          color: var(--color-light-textMuted);
          margin: 0;
          line-height: 1.6;
        }
      `}</style>

      <div className="ui-preview-container">
        {/* Hero Banner */}
        <div className="hero-banner">
          <h1>MarketIntel UI/UX Design System</h1>
          <p>A comprehensive preview of the new glassy, light, and techy aesthetic with all components and design patterns</p>
        </div>

        {/* Buttons Section */}
        <div className="section">
          <h2 className="section-title">Buttons</h2>
          <div className="component-showcase">
            <div className="component-label">Primary Buttons</div>
            <div className="button-group">
              <Btn variant="primary" size="sm">Small Button</Btn>
              <Btn variant="primary" size="md">Medium Button</Btn>
              <Btn variant="primary" size="lg">Large Button</Btn>
              <Btn variant="primary" size="md" loading>Loading</Btn>
            </div>

            <div style={{ marginTop: '24px' }} className="component-label">Secondary Buttons</div>
            <div className="button-group">
              <Btn variant="secondary" size="md">Secondary</Btn>
              <Btn variant="outline" size="md">Outline</Btn>
              <Btn variant="success" size="md">Success</Btn>
              <Btn variant="danger" size="md">Danger</Btn>
              <Btn variant="ghost" size="md">Ghost</Btn>
            </div>
          </div>
        </div>

        {/* Form Components Section */}
        <div className="section">
          <h2 className="section-title">Form Components</h2>
          <div className="component-showcase">
            <div className="form-group">
              <Field label="Text Input" htmlFor="text-input" hint="This is a helpful hint">
                <Input id="text-input" placeholder="Enter text..." value={inputValue} onChange={(e) => setInputValue(e.target.value)} />
              </Field>
            </div>

            <div className="form-group">
              <Field label="Select Dropdown" htmlFor="select-input">
                <Select id="select-input" value={selectValue} onChange={(e) => setSelectValue(e.target.value)}>
                  <option value="option1">Option 1</option>
                  <option value="option2">Option 2</option>
                  <option value="option3">Option 3</option>
                </Select>
              </Field>
            </div>

            <div className="form-group">
              <Field label="Textarea" htmlFor="textarea-input" hint="Multi-line text input">
                <Textarea id="textarea-input" placeholder="Enter multiple lines..." value={textareaValue} onChange={(e) => setTextareaValue(e.target.value)} rows={4} />
              </Field>
            </div>

            <div className="form-group">
              <Field label="Required Field" htmlFor="required-input" required error="This field is required">
                <Input id="required-input" placeholder="This field has an error..." />
              </Field>
            </div>
          </div>
        </div>

        {/* Cards Section */}
        <div className="section">
          <h2 className="section-title">Cards</h2>
          <div className="component-grid">
            <Card hover>
              <div style={{ marginBottom: '12px', fontSize: '10px', color: 'var(--color-light-textMuted)', fontFamily: 'IBM Plex Mono, monospace', textTransform: 'uppercase', letterSpacing: '0.1em' }}>CARD TITLE</div>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: '600', color: 'var(--color-light-text)' }}>Standard Card</h3>
              <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-light-textMuted)', lineHeight: '1.6' }}>This is a standard card with hover effect. It demonstrates the glassmorphic design pattern with subtle blur and transparency.</p>
            </Card>

            <Card>
              <div style={{ marginBottom: '12px', fontSize: '10px', color: 'var(--color-light-textMuted)', fontFamily: 'IBM Plex Mono, monospace', textTransform: 'uppercase', letterSpacing: '0.1em' }}>COMPACT CARD</div>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: '600', color: 'var(--color-light-text)' }}>Compact Layout</h3>
              <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-light-textMuted)', lineHeight: '1.6' }}>Smaller padding for dense information layouts.</p>
            </Card>

            <Card padding="32px">
              <div style={{ marginBottom: '12px', fontSize: '10px', color: 'var(--color-light-textMuted)', fontFamily: 'IBM Plex Mono, monospace', textTransform: 'uppercase', letterSpacing: '0.1em' }}>SPACIOUS CARD</div>
              <h3 style={{ margin: '0 0 8px 0', fontSize: '16px', fontWeight: '600', color: 'var(--color-light-text)' }}>Spacious Layout</h3>
              <p style={{ margin: 0, fontSize: '13px', color: 'var(--color-light-textMuted)', lineHeight: '1.6' }}>Extra padding for featured content and prominent information.</p>
            </Card>
          </div>
        </div>

        {/* Badges Section */}
        <div className="section">
          <h2 className="section-title">Badges</h2>
          <div className="component-showcase">
            <div className="component-label">Badge Variants</div>
            <div className="badge-group">
              <Badge variant="neutral">Neutral</Badge>
              <Badge variant="success">Success</Badge>
              <Badge variant="danger">Danger</Badge>
              <Badge variant="amber">Amber</Badge>
              <Badge variant="purple">Purple</Badge>
              <Badge variant="blue">Blue</Badge>
            </div>
          </div>
        </div>

        {/* Alerts Section */}
        <div className="section">
          <h2 className="section-title">Alerts</h2>
          <div className="component-showcase">
            <div style={{ marginBottom: '16px' }}>
              <Alert type="info">This is an informational alert message.</Alert>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <Alert type="success">This is a success alert message.</Alert>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <Alert type="warning">This is a warning alert message.</Alert>
            </div>
            <div>
              <Alert type="error">This is an error alert message.</Alert>
            </div>
          </div>
        </div>

        {/* Stat Cards Section */}
        <div className="section">
          <h2 className="section-title">Stat Cards</h2>
          <div className="stat-grid">
            <StatCard label="Total Products" value="1,247" color="var(--color-amber-500)" sub="↑ 12% from last month" />
            <StatCard label="Active Alerts" value="48" color="var(--color-signal-up)" sub="All systems operational" />
            <StatCard label="Competitor Activity" value="156" color="var(--color-signal-down)" sub="↑ 8 new competitors" />
            <StatCard label="Avg Price Change" value="+2.4%" color="var(--color-signal-up)" sub="Market trending up" mono={false} />
          </div>
        </div>

        {/* Color Palette Section */}
        <div className="section">
          <h2 className="section-title">Color Palette</h2>
          <div className="component-showcase">
            <div className="component-label">Light Theme Colors</div>
            <div className="color-swatch">
              <div className="color-box" style={{ backgroundColor: '#F0F0FA' }}></div>
              <div className="color-info">
                <div className="color-name">Background</div>
                <div className="color-value">#F0F0FA</div>
              </div>
            </div>
            <div className="color-swatch">
              <div className="color-box" style={{ backgroundColor: '#FFFFFF' }}></div>
              <div className="color-info">
                <div className="color-name">Surface</div>
                <div className="color-value">#FFFFFF</div>
              </div>
            </div>
            <div className="color-swatch">
              <div className="color-box" style={{ backgroundColor: '#E0E0E0' }}></div>
              <div className="color-info">
                <div className="color-name">Border</div>
                <div className="color-value">#E0E0E0</div>
              </div>
            </div>
            <div className="color-swatch">
              <div className="color-box" style={{ backgroundColor: '#0A0A0F' }}></div>
              <div className="color-info">
                <div className="color-name">Text</div>
                <div className="color-value">#0A0A0F</div>
              </div>
            </div>
            <div className="color-swatch">
              <div className="color-box" style={{ backgroundColor: '#606080' }}></div>
              <div className="color-info">
                <div className="color-name">Text Muted</div>
                <div className="color-value">#606080</div>
              </div>
            </div>
            <div className="color-swatch">
              <div className="color-box" style={{ backgroundColor: '#F59E0B' }}></div>
              <div className="color-info">
                <div className="color-name">Accent (Amber)</div>
                <div className="color-value">#F59E0B</div>
              </div>
            </div>
            <div className="color-swatch">
              <div className="color-box" style={{ backgroundColor: '#10B981' }}></div>
              <div className="color-info">
                <div className="color-name">Success</div>
                <div className="color-value">#10B981</div>
              </div>
            </div>
            <div className="color-swatch">
              <div className="color-box" style={{ backgroundColor: '#EF4444' }}></div>
              <div className="color-info">
                <div className="color-name">Danger</div>
                <div className="color-value">#EF4444</div>
              </div>
            </div>
          </div>
        </div>

        {/* Typography Section */}
        <div className="section">
          <h2 className="section-title">Typography</h2>
          <div className="component-showcase">
            <div className="typography-demo">
              <h1>Page Title (H1) - Syne 28px Bold</h1>
              <p>This is the main page heading using Syne font family with 800 font weight.</p>
            </div>
            <Divider />
            <div className="typography-demo">
              <h2>Section Header (H2) - Syne 18px Bold</h2>
              <p>This is a section heading using Syne font family with 700 font weight.</p>
            </div>
            <Divider />
            <div className="typography-demo">
              <p><strong>Body Text (14px Regular)</strong> - This is standard body text using IBM Plex Sans. It's used for most content in the application and should be comfortable to read for extended periods.</p>
            </div>
            <Divider />
            <div className="typography-demo">
              <p><code>Monospace Data (13px)</code> - This is monospace text using IBM Plex Mono. It's used for technical information, API keys, and data values.</p>
            </div>
          </div>
        </div>

        {/* Data Table Section */}
        <div className="section">
          <h2 className="section-title">Data Tables</h2>
          <div className="component-showcase">
            <table className="demo-table">
              <thead>
                <tr>
                  <th>Product Name</th>
                  <th>Current Price</th>
                  <th>Change</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>Premium Widget Pro</td>
                  <td>$89.99</td>
                  <td style={{ color: 'var(--color-signal-up)' }}>+2.4%</td>
                  <td><Badge variant="success">Active</Badge></td>
                </tr>
                <tr>
                  <td>Standard Widget</td>
                  <td>$49.99</td>
                  <td style={{ color: 'var(--color-signal-down)' }}>-1.2%</td>
                  <td><Badge variant="neutral">Monitoring</Badge></td>
                </tr>
                <tr>
                  <td>Budget Widget Lite</td>
                  <td>$29.99</td>
                  <td style={{ color: 'var(--color-signal-up)' }}>+0.8%</td>
                  <td><Badge variant="success">Active</Badge></td>
                </tr>
                <tr>
                  <td>Enterprise Widget Suite</td>
                  <td>$199.99</td>
                  <td style={{ color: 'var(--color-signal-up)' }}>+5.2%</td>
                  <td><Badge variant="amber">Alert</Badge></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Empty State Section */}
        <div className="section">
          <h2 className="section-title">Empty States</h2>
          <div className="component-grid">
            <EmptyState
              title="No Data Available"
              body="There are no items to display at this time. Try adjusting your filters or create a new item to get started."
              action={<Btn variant="primary" size="md">Create New Item</Btn>}
            />
          </div>
        </div>

        {/* Footer */}
        <div style={{ textAlign: 'center', marginTop: '60px', paddingTop: '40px', borderTop: '1px solid var(--color-light-border)' }}>
          <p style={{ fontSize: '12px', color: 'var(--color-light-textMuted)', margin: 0 }}>MarketIntel UI/UX Design System v1.0 • All components are fully responsive and accessible</p>
        </div>
      </div>
    </div>
  );
}
