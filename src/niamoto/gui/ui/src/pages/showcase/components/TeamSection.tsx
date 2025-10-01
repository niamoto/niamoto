import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Users,
  Mail,
  Github,
  Globe,
  Heart,
  Code,
  BookOpen
} from 'lucide-react'

const team = [
  {
    name: 'Équipe Niamoto',
    role: 'Développement & Recherche',
    description: 'Scientifiques, développeurs et écologistes passionnés par la biodiversité',
    icon: Users,
    color: 'text-green-600',
    bgColor: 'bg-green-600/10'
  }
]

const contributors = [
  {
    category: 'Core Contributors',
    members: [
      'Développeurs Python',
      'Experts en biodiversité',
      'Data scientists',
      'Designers UI/UX'
    ]
  },
  {
    category: 'Community',
    members: [
      'Contributeurs open-source',
      'Utilisateurs beta-testeurs',
      'Chercheurs partenaires',
      'Institutions partenaires'
    ]
  }
]

const links = [
  {
    name: 'GitHub',
    icon: Github,
    url: 'https://github.com/niamoto/niamoto',
    description: 'Code source et contributions'
  },
  {
    name: 'Documentation',
    icon: BookOpen,
    url: '#',
    description: 'Guides et tutoriels'
  },
  {
    name: 'Contact',
    icon: Mail,
    url: 'mailto:contact@niamoto.nc',
    description: 'Nous contacter'
  }
]

export function TeamSection() {
  return (
    <div className="w-full max-w-6xl mx-auto space-y-12 py-12">
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-3 mb-4">
          <Heart className="w-8 h-8 text-red-500 fill-red-500" />
          <h2 className="text-4xl font-bold">Équipe & Communauté</h2>
          <Heart className="w-8 h-8 text-red-500 fill-red-500" />
        </div>
        <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
          Projet collaboratif open-source pour la conservation de la biodiversité
        </p>
      </div>

      {/* Main Team Card */}
      <div className="grid grid-cols-1 gap-6">
        {team.map((member) => {
          const Icon = member.icon
          return (
            <Card key={member.name} className="border-2 hover:shadow-xl transition-all">
              <CardHeader>
                <div className="flex items-center gap-4">
                  <div className={`w-16 h-16 rounded-full ${member.bgColor} flex items-center justify-center`}>
                    <Icon className={`w-8 h-8 ${member.color}`} />
                  </div>
                  <div>
                    <CardTitle className="text-2xl">{member.name}</CardTitle>
                    <CardDescription className="text-lg">{member.role}</CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-muted-foreground">{member.description}</p>
              </CardContent>
            </Card>
          )
        })}
      </div>

      {/* Contributors Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {contributors.map((group) => (
          <Card key={group.category}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Code className="w-5 h-5" />
                {group.category}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                {group.members.map((member) => (
                  <Badge key={member} variant="secondary" className="text-sm py-1.5">
                    {member}
                  </Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Links & Contact */}
      <Card className="bg-gradient-to-br from-primary/5 to-primary/10 border-primary/20">
        <CardHeader>
          <CardTitle>Rejoignez-nous</CardTitle>
          <CardDescription>
            Contribuez au projet ou contactez-nous pour en savoir plus
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {links.map((link) => {
              const Icon = link.icon
              return (
                <Button
                  key={link.name}
                  variant="outline"
                  className="h-auto flex-col items-start p-4 hover:bg-primary/10"
                  asChild
                >
                  <a
                    href={link.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="w-full"
                  >
                    <div className="flex items-center gap-2 mb-2 w-full">
                      <Icon className="w-5 h-5" />
                      <span className="font-semibold">{link.name}</span>
                    </div>
                    <p className="text-xs text-muted-foreground text-left">
                      {link.description}
                    </p>
                  </a>
                </Button>
              )
            })}
          </div>
        </CardContent>
      </Card>

      {/* Open Source Notice */}
      <Card className="text-center border-dashed">
        <CardContent className="pt-6">
          <div className="flex items-center justify-center gap-2 mb-3">
            <Globe className="w-5 h-5 text-green-600" />
            <Badge variant="outline" className="text-green-600 border-green-600">
              Open Source
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground max-w-2xl mx-auto">
            Niamoto est un projet open-source sous licence MIT. Toutes les contributions sont les bienvenues !
            <br />
            <span className="text-xs opacity-75">
              Développé avec passion pour la conservation de la biodiversité mondiale
            </span>
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
