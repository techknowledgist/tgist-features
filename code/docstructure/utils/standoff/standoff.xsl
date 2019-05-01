<!-- Convert an inline XML document to a standoff representation. -->
<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:standoff="http://timeml.org/standoff">
<xsl:output method="xml" encoding="UTF-8"/>

<!-- Elements are copied with their attributes, to which we add our own two
     standoff attributes: offset and length. -->
<xsl:template match="*">
  <xsl:param name="offset" select="0"/>
  <xsl:variable name="length" select="string-length(.)"/>

  <xsl:copy>
    <xsl:for-each select="@*">
      <xsl:copy/>
    </xsl:for-each>
    <xsl:attribute name="standoff:offset">
      <xsl:value-of select="$offset"/>
    </xsl:attribute>
    <xsl:attribute name="standoff:length">
      <xsl:value-of select="$length"/>
    </xsl:attribute>

    <xsl:apply-templates select="child::node()[1]">
      <xsl:with-param name="offset" select="$offset"/>
    </xsl:apply-templates>
  </xsl:copy>

  <xsl:apply-templates select="following-sibling::node()[1]">
    <xsl:with-param name="offset" select="$offset+$length"/>
  </xsl:apply-templates>
</xsl:template>

<!-- Text nodes are noted using standoff:text elements, and they serve
     to increment the offset of their following sibling by their length. -->
<xsl:template match="text()">
  <xsl:param name="offset" select="0"/>
  <xsl:variable name="length" select="string-length(.)"/>

  <standoff:text standoff:offset="{$offset}" standoff:length="{$length}"/>

  <xsl:apply-templates select="following-sibling::node()[1]">
    <xsl:with-param name="offset" select="$offset+$length"/>
  </xsl:apply-templates>
</xsl:template>

<!-- Processing instructions in the source document are transformed into
     standoff:processing-instruction elements so that we can attach
     standoff:offset attributes to them. These elements are modeled on
     xsl:processing-instruction: they have a name attribute that contains
     the name of the processing instruction node, and their contents are
     the part of the PI following the name. They are always treated as
     having zero length. -->
<xsl:template match="processing-instruction()">
  <xsl:param name="offset" select="0"/>

  <standoff:processing-instruction name="{local-name()}"
                                   standoff:offset="{$offset}">
    <xsl:value-of select="string()"/>
  </standoff:processing-instruction>

  <xsl:apply-templates select="following-sibling::node()[1]">
    <xsl:with-param name="offset" select="$offset"/>
  </xsl:apply-templates>
</xsl:template>

<!-- Comments are handled similarly to processing isntructions, and for
     the same reason. -->
<xsl:template match="comment()">
  <xsl:param name="offset" select="0"/>

  <standoff:comment standoff:offset="{$offset}">
    <xsl:value-of select="string()"/>
  </standoff:comment>

  <xsl:apply-templates select="following-sibling::node()[1]">
    <xsl:with-param name="offset" select="$offset"/>
  </xsl:apply-templates>
</xsl:template>

<!-- Comments and processing instructions in the prolog (i.e., before the
     root element) are passed straight through. -->
<xsl:template match="/comment()|/processing-instruction()">
  <xsl:copy/>
</xsl:template>

</xsl:stylesheet>
