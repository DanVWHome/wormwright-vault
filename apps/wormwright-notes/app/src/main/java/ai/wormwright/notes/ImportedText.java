package ai.wormwright.notes;
import java.util.regex.*;

/** Text-only normalization. Never interprets HTML, URLs, instructions or note IDs. */
final class ImportedText {
    static final int MAX_TEXT=100000,MAX_TITLE=200,MAX_ITEMS=1000;
    static final Pattern MARKER=Pattern.compile("^(?:[-*+•‣]\\s+)?\\[([ xX])\\]\\s*(.*)$");
    static final Pattern BULLET=Pattern.compile("^(?:[-*+•‣]\\s+|\\d{1,4}[.)]\\s+)(.*)$");
    static String validate(String text){
        if(text==null||text.trim().isEmpty())throw new IllegalArgumentException("Add some text before saving");
        if(text.length()>MAX_TEXT)throw new IllegalArgumentException("Use no more than 100,000 characters per import");
        return text.replace("\r\n","\n").replace('\r','\n');
    }
    static String body(String text,boolean checklist){
        String value=validate(text);if(!checklist)return value;
        StringBuilder result=new StringBuilder();int count=0;
        for(String line:value.split("\n",-1)){
            String item=line.trim();if(item.isEmpty())continue;
            boolean checked=false;Matcher marker=MARKER.matcher(item);
            if(marker.matches()){checked=!marker.group(1).equals(" ");item=marker.group(2);}
            else if(item.startsWith("☑")||item.startsWith("☐")||item.startsWith("✅")){
                checked=!item.startsWith("☐");item=item.substring(1).trim();
            }else{Matcher bullet=BULLET.matcher(item);if(bullet.matches())item=bullet.group(1);}
            if(item.trim().isEmpty())continue;
            if(++count>MAX_ITEMS)throw new IllegalArgumentException("Use no more than 1,000 checklist items");
            if(result.length()>0)result.append('\n');result.append(checked?"[x] ":"[ ] ").append(item.trim());
        }
        if(count==0)throw new IllegalArgumentException("Add at least one checklist item");
        return result.toString();
    }
    static String title(String value,boolean checklist){
        String text=value==null?"":value.trim();
        if(text.length()>MAX_TITLE)throw new IllegalArgumentException("Use a title of 200 characters or fewer");
        return text.isEmpty()?(checklist?"Imported checklist":"Imported note"):text;
    }
}
