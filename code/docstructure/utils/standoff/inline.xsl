<!-- Go from a standoff representation back to inline XML. -->
<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:standoff="http://timeml.org/standoff"
                exclude-result-prefixes="standoff">
<xsl:output method="xml" encoding="UTF-8"/>

<!-- This parameter should be passed in by the XSLT processor.
     E.g., for xsltproc(1), use the stringparam option.  -->
<xsl:param name="text"/>

<!-- Elements are copied through, but we strip off all standoff attributes. -->
<xsl:template match="*">
  <xsl:copy>
    <xsl:for-each select="@*[namespace-uri()!='http://timeml.org/standoff']">
      <xsl:copy/>
    </xsl:for-each>
    <xsl:apply-templates/>
  </xsl:copy>
</xsl:template>

<!-- standoff:text elements construct text nodes in the output. -->
<xsl:template match="standoff:text">
  <xsl:value-of
      select="substring($text, @standoff:offset+1, @standoff:length)"/>
</xsl:template>

<!-- standoff:processing-instruction elements construct processing
     instructions in the output. -->
<xsl:template match="standoff:processing-instruction">
  <xsl:processing-instruction name="{@name}">
    <xsl:value-of select="string()"/>
  </xsl:processing-instruction>
</xsl:template>

<!-- And similarly for standoff:comment elements. -->
<xsl:template match="standoff:comment">
  <xsl:comment>
    <xsl:value-of select="string()"/>
  </xsl:comment>
</xsl:template>

<!-- Actual processing instructions and comments in the source are just
     copied through. -->
<xsl:template match="processing-instruction()|comment()">
  <xsl:copy/>
</xsl:template>

<!-- Text nodes in the standoff document are completely ignored. -->
<xsl:template match="text()">
</xsl:template>

</xsl:stylesheet>
