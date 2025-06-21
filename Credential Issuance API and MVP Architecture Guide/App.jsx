import { useState, useRef, useCallback } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Textarea } from '@/components/ui/textarea.jsx'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select.jsx'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { Separator } from '@/components/ui/separator.jsx'
import { 
  Type, 
  Image as ImageIcon, 
  Square, 
  Circle, 
  QrCode, 
  Upload, 
  Download, 
  Eye, 
  Save, 
  Trash2,
  Copy,
  Palette,
  Move,
  RotateCcw,
  ZoomIn,
  ZoomOut,
  Grid,
  Layers
} from 'lucide-react'
import './App.css'

function App() {
  const [selectedTemplate, setSelectedTemplate] = useState(null)
  const [templateName, setTemplateName] = useState('')
  const [templateDescription, setTemplateDescription] = useState('')
  const [templateType, setTemplateType] = useState('certificate')
  const [canvasElements, setCanvasElements] = useState([])
  const [selectedElement, setSelectedElement] = useState(null)
  const [canvasSize, setCanvasSize] = useState({ width: 1200, height: 800 })
  const [zoom, setZoom] = useState(1)
  const [showGrid, setShowGrid] = useState(true)
  const canvasRef = useRef(null)

  // Default template designs
  const defaultTemplates = {
    certificate: {
      name: "Classic Certificate",
      type: "certificate",
      size: { width: 1200, height: 800 },
      elements: [
        {
          id: 'title',
          type: 'text',
          content: 'CERTIFICATE OF ACHIEVEMENT',
          x: 600,
          y: 100,
          width: 800,
          height: 60,
          style: {
            fontSize: 36,
            fontFamily: 'Arial',
            fontWeight: 'bold',
            color: '#2563EB',
            textAlign: 'center'
          }
        },
        {
          id: 'recipient_name',
          type: 'text',
          content: '{{recipient_name}}',
          x: 600,
          y: 300,
          width: 600,
          height: 50,
          style: {
            fontSize: 28,
            fontFamily: 'Arial',
            fontWeight: 'bold',
            color: '#1F2937',
            textAlign: 'center'
          }
        }
      ]
    },
    badge: {
      name: "Digital Badge",
      type: "badge",
      size: { width: 400, height: 400 },
      elements: [
        {
          id: 'badge_icon',
          type: 'text',
          content: '🏆',
          x: 200,
          y: 120,
          width: 80,
          height: 80,
          style: {
            fontSize: 60,
            textAlign: 'center'
          }
        },
        {
          id: 'title',
          type: 'text',
          content: '{{title}}',
          x: 200,
          y: 220,
          width: 300,
          height: 40,
          style: {
            fontSize: 18,
            fontFamily: 'Arial',
            fontWeight: 'bold',
            color: '#ffffff',
            textAlign: 'center'
          }
        }
      ]
    }
  }

  const loadTemplate = (templateKey) => {
    const template = defaultTemplates[templateKey]
    setSelectedTemplate(template)
    setTemplateName(template.name)
    setTemplateType(template.type)
    setCanvasSize(template.size)
    setCanvasElements(template.elements)
    setSelectedElement(null)
  }

  const addElement = (elementType) => {
    const newElement = {
      id: `element_${Date.now()}`,
      type: elementType,
      content: elementType === 'text' ? 'New Text' : '',
      x: 100,
      y: 100,
      width: elementType === 'text' ? 200 : 100,
      height: elementType === 'text' ? 40 : 100,
      style: {
        fontSize: 16,
        fontFamily: 'Arial',
        color: '#000000',
        backgroundColor: elementType === 'shape' ? '#E5E7EB' : 'transparent',
        textAlign: 'left'
      }
    }
    
    setCanvasElements([...canvasElements, newElement])
    setSelectedElement(newElement)
  }

  const updateElement = (elementId, updates) => {
    setCanvasElements(elements => 
      elements.map(el => 
        el.id === elementId ? { ...el, ...updates } : el
      )
    )
    
    if (selectedElement && selectedElement.id === elementId) {
      setSelectedElement({ ...selectedElement, ...updates })
    }
  }

  const deleteElement = (elementId) => {
    setCanvasElements(elements => elements.filter(el => el.id !== elementId))
    if (selectedElement && selectedElement.id === elementId) {
      setSelectedElement(null)
    }
  }

  const duplicateElement = (element) => {
    const newElement = {
      ...element,
      id: `element_${Date.now()}`,
      x: element.x + 20,
      y: element.y + 20
    }
    setCanvasElements([...canvasElements, newElement])
  }

  const handleCanvasClick = (e) => {
    const rect = canvasRef.current.getBoundingClientRect()
    const x = (e.clientX - rect.left) / zoom
    const y = (e.clientY - rect.top) / zoom
    
    // Check if clicked on an element
    const clickedElement = canvasElements.find(el => 
      x >= el.x - el.width/2 && 
      x <= el.x + el.width/2 && 
      y >= el.y - el.height/2 && 
      y <= el.y + el.height/2
    )
    
    setSelectedElement(clickedElement || null)
  }

  const renderElement = (element) => {
    const style = {
      position: 'absolute',
      left: `${element.x - element.width/2}px`,
      top: `${element.y - element.height/2}px`,
      width: `${element.width}px`,
      height: `${element.height}px`,
      fontSize: `${element.style.fontSize}px`,
      fontFamily: element.style.fontFamily,
      fontWeight: element.style.fontWeight,
      color: element.style.color,
      backgroundColor: element.style.backgroundColor,
      textAlign: element.style.textAlign,
      display: 'flex',
      alignItems: 'center',
      justifyContent: element.style.textAlign === 'center' ? 'center' : 'flex-start',
      border: selectedElement?.id === element.id ? '2px solid #3B82F6' : 'none',
      cursor: 'pointer',
      userSelect: 'none'
    }

    return (
      <div
        key={element.id}
        style={style}
        onClick={(e) => {
          e.stopPropagation()
          setSelectedElement(element)
        }}
      >
        {element.type === 'text' && element.content}
        {element.type === 'shape' && <div className="w-full h-full bg-current opacity-50" />}
        {element.type === 'qr_code' && <QrCode className="w-full h-full" />}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Design Studio</h1>
            <p className="text-gray-600">Create and customize credential templates</p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="outline" size="sm">
              <Eye className="w-4 h-4 mr-2" />
              Preview
            </Button>
            <Button variant="outline" size="sm">
              <Save className="w-4 h-4 mr-2" />
              Save Draft
            </Button>
            <Button size="sm">
              <Download className="w-4 h-4 mr-2" />
              Publish
            </Button>
          </div>
        </div>
      </header>

      <div className="flex h-[calc(100vh-80px)]">
        {/* Left Sidebar - Templates & Elements */}
        <div className="w-80 bg-white border-r border-gray-200 overflow-y-auto">
          <Tabs defaultValue="templates" className="w-full">
            <TabsList className="grid w-full grid-cols-2 m-4">
              <TabsTrigger value="templates">Templates</TabsTrigger>
              <TabsTrigger value="elements">Elements</TabsTrigger>
            </TabsList>
            
            <TabsContent value="templates" className="px-4 pb-4">
              <div className="space-y-4">
                <div>
                  <Label htmlFor="template-name">Template Name</Label>
                  <Input
                    id="template-name"
                    value={templateName}
                    onChange={(e) => setTemplateName(e.target.value)}
                    placeholder="Enter template name"
                  />
                </div>
                
                <div>
                  <Label htmlFor="template-description">Description</Label>
                  <Textarea
                    id="template-description"
                    value={templateDescription}
                    onChange={(e) => setTemplateDescription(e.target.value)}
                    placeholder="Template description"
                    rows={3}
                  />
                </div>
                
                <div>
                  <Label htmlFor="template-type">Type</Label>
                  <Select value={templateType} onValueChange={setTemplateType}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="certificate">Certificate</SelectItem>
                      <SelectItem value="badge">Badge</SelectItem>
                      <SelectItem value="diploma">Diploma</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <Separator />

                <div>
                  <h3 className="font-semibold mb-3">Default Templates</h3>
                  <div className="space-y-2">
                    {Object.entries(defaultTemplates).map(([key, template]) => (
                      <Card 
                        key={key} 
                        className="cursor-pointer hover:bg-gray-50 transition-colors"
                        onClick={() => loadTemplate(key)}
                      >
                        <CardContent className="p-3">
                          <div className="flex items-center justify-between">
                            <div>
                              <h4 className="font-medium">{template.name}</h4>
                              <Badge variant="secondary" className="text-xs">
                                {template.type}
                              </Badge>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              </div>
            </TabsContent>
            
            <TabsContent value="elements" className="px-4 pb-4">
              <div className="space-y-4">
                <div>
                  <h3 className="font-semibold mb-3">Add Elements</h3>
                  <div className="grid grid-cols-2 gap-2">
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => addElement('text')}
                      className="flex flex-col h-16 gap-1"
                    >
                      <Type className="w-5 h-5" />
                      <span className="text-xs">Text</span>
                    </Button>
                    
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => addElement('image')}
                      className="flex flex-col h-16 gap-1"
                    >
                      <ImageIcon className="w-5 h-5" />
                      <span className="text-xs">Image</span>
                    </Button>
                    
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => addElement('shape')}
                      className="flex flex-col h-16 gap-1"
                    >
                      <Square className="w-5 h-5" />
                      <span className="text-xs">Shape</span>
                    </Button>
                    
                    <Button 
                      variant="outline" 
                      size="sm" 
                      onClick={() => addElement('qr_code')}
                      className="flex flex-col h-16 gap-1"
                    >
                      <QrCode className="w-5 h-5" />
                      <span className="text-xs">QR Code</span>
                    </Button>
                  </div>
                </div>

                <Separator />

                <div>
                  <h3 className="font-semibold mb-3">Upload Assets</h3>
                  <Button variant="outline" size="sm" className="w-full">
                    <Upload className="w-4 h-4 mr-2" />
                    Upload Image
                  </Button>
                </div>

                <Separator />

                <div>
                  <h3 className="font-semibold mb-3">Layers</h3>
                  <div className="space-y-1">
                    {canvasElements.map((element, index) => (
                      <div 
                        key={element.id}
                        className={`flex items-center justify-between p-2 rounded text-sm cursor-pointer ${
                          selectedElement?.id === element.id ? 'bg-blue-50 border border-blue-200' : 'hover:bg-gray-50'
                        }`}
                        onClick={() => setSelectedElement(element)}
                      >
                        <div className="flex items-center gap-2">
                          <Layers className="w-3 h-3" />
                          <span className="truncate">
                            {element.type === 'text' ? element.content : element.type}
                          </span>
                        </div>
                        <div className="flex gap-1">
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-6 w-6 p-0"
                            onClick={(e) => {
                              e.stopPropagation()
                              duplicateElement(element)
                            }}
                          >
                            <Copy className="w-3 h-3" />
                          </Button>
                          <Button 
                            variant="ghost" 
                            size="sm" 
                            className="h-6 w-6 p-0 text-red-500 hover:text-red-700"
                            onClick={(e) => {
                              e.stopPropagation()
                              deleteElement(element.id)
                            }}
                          >
                            <Trash2 className="w-3 h-3" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </TabsContent>
          </Tabs>
        </div>

        {/* Main Canvas Area */}
        <div className="flex-1 flex flex-col">
          {/* Canvas Toolbar */}
          <div className="bg-white border-b border-gray-200 px-4 py-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setZoom(Math.max(0.25, zoom - 0.25))}
                >
                  <ZoomOut className="w-4 h-4" />
                </Button>
                <span className="text-sm font-medium min-w-16 text-center">
                  {Math.round(zoom * 100)}%
                </span>
                <Button 
                  variant="outline" 
                  size="sm"
                  onClick={() => setZoom(Math.min(2, zoom + 0.25))}
                >
                  <ZoomIn className="w-4 h-4" />
                </Button>
                
                <Separator orientation="vertical" className="h-6 mx-2" />
                
                <Button 
                  variant={showGrid ? "default" : "outline"} 
                  size="sm"
                  onClick={() => setShowGrid(!showGrid)}
                >
                  <Grid className="w-4 h-4" />
                </Button>
              </div>
              
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <span>{canvasSize.width} × {canvasSize.height}px</span>
              </div>
            </div>
          </div>

          {/* Canvas */}
          <div className="flex-1 overflow-auto bg-gray-100 p-8">
            <div className="flex justify-center">
              <div 
                ref={canvasRef}
                className="relative bg-white shadow-lg"
                style={{
                  width: `${canvasSize.width * zoom}px`,
                  height: `${canvasSize.height * zoom}px`,
                  transform: `scale(${zoom})`,
                  transformOrigin: 'top left'
                }}
                onClick={handleCanvasClick}
              >
                {/* Grid */}
                {showGrid && (
                  <div 
                    className="absolute inset-0 opacity-20"
                    style={{
                      backgroundImage: `
                        linear-gradient(to right, #e5e7eb 1px, transparent 1px),
                        linear-gradient(to bottom, #e5e7eb 1px, transparent 1px)
                      `,
                      backgroundSize: '20px 20px'
                    }}
                  />
                )}
                
                {/* Elements */}
                {canvasElements.map(renderElement)}
              </div>
            </div>
          </div>
        </div>

        {/* Right Sidebar - Properties */}
        <div className="w-80 bg-white border-l border-gray-200 overflow-y-auto">
          <div className="p-4">
            {selectedElement ? (
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">Element Properties</h3>
                  <Badge variant="secondary">{selectedElement.type}</Badge>
                </div>
                
                {selectedElement.type === 'text' && (
                  <div className="space-y-3">
                    <div>
                      <Label>Content</Label>
                      <Textarea
                        value={selectedElement.content}
                        onChange={(e) => updateElement(selectedElement.id, { content: e.target.value })}
                        rows={3}
                      />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <Label>Font Size</Label>
                        <Input
                          type="number"
                          value={selectedElement.style.fontSize}
                          onChange={(e) => updateElement(selectedElement.id, {
                            style: { ...selectedElement.style, fontSize: parseInt(e.target.value) }
                          })}
                        />
                      </div>
                      <div>
                        <Label>Color</Label>
                        <Input
                          type="color"
                          value={selectedElement.style.color}
                          onChange={(e) => updateElement(selectedElement.id, {
                            style: { ...selectedElement.style, color: e.target.value }
                          })}
                        />
                      </div>
                    </div>
                    
                    <div>
                      <Label>Font Family</Label>
                      <Select 
                        value={selectedElement.style.fontFamily}
                        onValueChange={(value) => updateElement(selectedElement.id, {
                          style: { ...selectedElement.style, fontFamily: value }
                        })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="Arial">Arial</SelectItem>
                          <SelectItem value="Times New Roman">Times New Roman</SelectItem>
                          <SelectItem value="Helvetica">Helvetica</SelectItem>
                          <SelectItem value="Georgia">Georgia</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    
                    <div>
                      <Label>Text Align</Label>
                      <Select 
                        value={selectedElement.style.textAlign}
                        onValueChange={(value) => updateElement(selectedElement.id, {
                          style: { ...selectedElement.style, textAlign: value }
                        })}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="left">Left</SelectItem>
                          <SelectItem value="center">Center</SelectItem>
                          <SelectItem value="right">Right</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                )}
                
                <Separator />
                
                <div className="space-y-3">
                  <h4 className="font-medium">Position & Size</h4>
                  
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label>X Position</Label>
                      <Input
                        type="number"
                        value={selectedElement.x}
                        onChange={(e) => updateElement(selectedElement.id, { x: parseInt(e.target.value) })}
                      />
                    </div>
                    <div>
                      <Label>Y Position</Label>
                      <Input
                        type="number"
                        value={selectedElement.y}
                        onChange={(e) => updateElement(selectedElement.id, { y: parseInt(e.target.value) })}
                      />
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-2">
                    <div>
                      <Label>Width</Label>
                      <Input
                        type="number"
                        value={selectedElement.width}
                        onChange={(e) => updateElement(selectedElement.id, { width: parseInt(e.target.value) })}
                      />
                    </div>
                    <div>
                      <Label>Height</Label>
                      <Input
                        type="number"
                        value={selectedElement.height}
                        onChange={(e) => updateElement(selectedElement.id, { height: parseInt(e.target.value) })}
                      />
                    </div>
                  </div>
                </div>
                
                <Separator />
                
                <div className="flex gap-2">
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => duplicateElement(selectedElement)}
                    className="flex-1"
                  >
                    <Copy className="w-4 h-4 mr-2" />
                    Duplicate
                  </Button>
                  <Button 
                    variant="outline" 
                    size="sm" 
                    onClick={() => deleteElement(selectedElement.id)}
                    className="text-red-600 hover:text-red-700"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>
              </div>
            ) : (
              <div className="text-center text-gray-500 py-8">
                <Palette className="w-12 h-12 mx-auto mb-3 opacity-50" />
                <p>Select an element to edit its properties</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

